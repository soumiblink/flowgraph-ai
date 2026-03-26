import sqlite3
from groq import Groq
import os
import re
from dotenv import load_dotenv   


load_dotenv()                   

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY not found. Set it in environment or Streamlit Secrets.")

client = Groq(api_key=api_key)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data.db")



def run_query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(sql, params)
    result = cursor.fetchall()
    conn.close()
    return result


def safe_run_query(sql, params=()):
    try:
        return run_query(sql, params)
    except Exception as e:
        return f"Query failed: {str(e)}"



def trace_full_flow(order_id):
    """Return the full O2C chain for a given sales order ID."""
    sql = """
        SELECT
            soh.salesOrder,
            soh.soldToParty,
            soh.totalNetAmount,
            odi.deliveryDocument,
            bdh.billingDocument,
            bdh.totalNetAmount  AS billedAmount,
            par.accountingDocument,
            par.amountInTransactionCurrency AS paidAmount
        FROM sales_order_headers soh
        LEFT JOIN outbound_delivery_items odi
            ON odi.referenceSdDocument = soh.salesOrder
        LEFT JOIN billing_document_items bdi
            ON bdi.referenceSdDocument = odi.deliveryDocument
        LEFT JOIN billing_document_headers bdh
            ON bdh.billingDocument = bdi.billingDocument
        LEFT JOIN payments_accounts_receivable par
            ON par.accountingDocument = bdh.accountingDocument
        WHERE soh.salesOrder = ?
        LIMIT 20
    """
    rows = safe_run_query(sql, (order_id,))
    if isinstance(rows, str):
        return rows
    if not rows:
        return f"No data found for order {order_id}."

    lines = [f"Full O2C flow for Sales Order {order_id}:\n"]
    for r in rows:
        order, customer, order_amt, delivery, billing, billed_amt, accounting, paid_amt = r
        lines.append(
            f"  Order {order} | Customer {customer} | Order Amount {order_amt}\n"
            f"    → Delivery: {delivery or 'MISSING'}\n"
            f"    → Billing:  {billing or 'MISSING'} (Amount: {billed_amt or 'N/A'})\n"
            f"    → Payment:  {accounting or 'MISSING'} (Paid: {paid_amt or 'N/A'})\n"
        )
    return "\n".join(lines)


def detect_incomplete_flows():
    """Return orders that are missing delivery, billing, or payment."""
    sql = """
        SELECT
            soh.salesOrder,
            soh.soldToParty,
            CASE WHEN odi.deliveryDocument IS NULL THEN 'No Delivery' ELSE 'Delivered' END AS delivery_status,
            CASE WHEN bdi.billingDocument IS NULL THEN 'Not Billed' ELSE 'Billed' END AS billing_status,
            CASE WHEN par.accountingDocument IS NULL THEN 'Unpaid' ELSE 'Paid' END AS payment_status
        FROM sales_order_headers soh
        LEFT JOIN outbound_delivery_items odi ON odi.referenceSdDocument = soh.salesOrder
        LEFT JOIN billing_document_items bdi ON bdi.referenceSdDocument = odi.deliveryDocument
        LEFT JOIN billing_document_headers bdh ON bdh.billingDocument = bdi.billingDocument
        LEFT JOIN payments_accounts_receivable par ON par.accountingDocument = bdh.accountingDocument
        WHERE odi.deliveryDocument IS NULL
           OR bdi.billingDocument IS NULL
           OR par.accountingDocument IS NULL
        LIMIT 20
    """
    rows = safe_run_query(sql)
    if isinstance(rows, str):
        return rows
    if not rows:
        return "All orders have complete flows — no gaps detected."

    lines = ["Incomplete O2C flows detected:\n"]
    for r in rows:
        order, customer, delivery, billing, payment = r
        lines.append(
            f"  Order {order} | Customer {customer} | "
            f"{delivery} | {billing} | {payment}"
        )
    return "\n".join(lines)



def generate_sql(query):
    prompt = f"""You are an expert SQL generator for a SAP Order-to-Cash analytics system.

TABLES AND COLUMNS (use ONLY these — do NOT invent columns):
1. sales_order_headers     (salesOrder, soldToParty, totalNetAmount, transactionCurrency, creationDate)
2. sales_order_items       (salesOrder, salesOrderItem, material, netAmount, requestedQuantity)
3. outbound_delivery_items (deliveryDocument, referenceSdDocument, referenceSdDocumentItem)
4. outbound_delivery_headers (deliveryDocument, shippingPoint, overallGoodsMovementStatus)
5. billing_document_items  (billingDocument, referenceSdDocument, material, netAmount)
6. billing_document_headers (billingDocument, accountingDocument, totalNetAmount, soldToParty, billingDocumentDate)
7. payments_accounts_receivable (accountingDocument, amountInTransactionCurrency, customer, postingDate)
8. business_partners       (businessPartner)
9. products                (product)

JOIN PATHS (use exactly these):
- sales_order_headers → outbound_delivery_items  via: odi.referenceSdDocument = soh.salesOrder
- outbound_delivery_items → billing_document_items via: bdi.referenceSdDocument = odi.deliveryDocument
- billing_document_items → billing_document_headers via: bdh.billingDocument = bdi.billingDocument
- billing_document_headers → payments_accounts_receivable via: par.accountingDocument = bdh.accountingDocument

SQL RULES:
- Return ONLY the SQL statement — no explanation, no markdown, no backticks
- Use GROUP BY for aggregation queries
- Use SUM() for revenue, COUNT() for volume
- Use ORDER BY ... DESC for rankings
- Use LIMIT 10 unless user specifies otherwise
- Use LEFT JOIN to detect missing/incomplete relationships

EXAMPLES:
Query: Which customers generate the highest revenue?
SQL: SELECT soldToParty, SUM(totalNetAmount) AS total_revenue FROM sales_order_headers GROUP BY soldToParty ORDER BY total_revenue DESC LIMIT 10;

Query: Which orders have no delivery?
SQL: SELECT soh.salesOrder FROM sales_order_headers soh LEFT JOIN outbound_delivery_items odi ON odi.referenceSdDocument = soh.salesOrder WHERE odi.deliveryDocument IS NULL LIMIT 10;

Query: Which products appear in the most billing documents?
SQL: SELECT bdi.material, COUNT(DISTINCT bdi.billingDocument) AS billing_count FROM billing_document_items bdi GROUP BY bdi.material ORDER BY billing_count DESC LIMIT 10;

User Query: {query}
SQL:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    sql = response.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    # Strip any leading "SQL:" the model may echo back
    if sql.upper().startswith("SQL:"):
        sql = sql[4:].strip()
    return sql



def format_result(result):
    if not result:
        return "No data found."
    return "\n".join(str(row) for row in result)


def generate_answer(query, result):
    formatted = format_result(result)
    prompt = f"""You are a business analyst presenting data to an executive.

User asked: {query}

Raw SQL result:
{formatted}

Instructions:
- Write a clear, structured answer using numbered lists or bullet points
- Lead with a one-sentence summary of the key finding
- Highlight the most important values (IDs, amounts, counts)
- If amounts are present, include totals or averages where useful
- Keep it concise — no filler text, no repetition
- Do not mention SQL or databases"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


def explain_result(query, result):
    prompt = f"""User Query: {query}
Data: {result}
In 2-3 sentences, explain what this means in plain business terms. No jargon."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()




DOMAIN_KEYWORDS = [
    "order", "delivery", "billing", "payment", "product", "customer",
    "invoice", "revenue", "sales", "shipment", "material", "flow",
    "trace", "incomplete", "missing", "billed", "paid", "unpaid"
]

OFF_TOPIC_PATTERNS = [
    r"\bjoke\b", r"\bweather\b", r"\bnews\b", r"\bwho is\b",
    r"\bwhat is the meaning\b", r"\bpolitics\b", r"\bsport\b",
    r"\brecipe\b", r"\bwrite a poem\b", r"\btell me about\b"
]


def is_valid_query(query):
    q = query.lower()
    if any(re.search(p, q) for p in OFF_TOPIC_PATTERNS):
        return False
    return any(k in q for k in DOMAIN_KEYWORDS)




def extract_order_id(query):
    match = re.search(r'\d{5,}', query)
    return match.group(0) if match else None


def is_trace_query(query):
    return any(w in query.lower() for w in ["trace", "flow", "full flow", "track", "follow"])


def is_incomplete_query(query):
    return any(w in query.lower() for w in ["missing", "incomplete", "broken", "no delivery",
                                              "not billed", "unpaid", "no billing", "no payment"])



def app(query):
    if not is_valid_query(query):
        return {
            "sql": "",
            "result": "This system answers questions about sales orders, deliveries, billing, and payments only.",
            "explanation": ""
        }

    
    if is_incomplete_query(query):
        result_text = detect_incomplete_flows()
        return {"sql": "(built-in incomplete flow query)", "result": result_text, "explanation": ""}

    
    if is_trace_query(query):
        order_id = extract_order_id(query)
        if order_id:
            result_text = trace_full_flow(order_id)
            return {"sql": f"(built-in trace for order {order_id})", "result": result_text, "explanation": ""}

    
    sql = generate_sql(query)
    result = safe_run_query(sql)

    if isinstance(result, str) and result.startswith("Query failed"):
        return {"sql": sql, "result": result, "explanation": ""}

    if not result:
        return {
            "sql": sql,
            "result": "No data found for this query.",
            "explanation": "No matching records exist in the dataset."
        }

    answer = generate_answer(query, result)
    explanation = explain_result(query, result)
    return {"sql": sql, "result": answer, "explanation": explanation}
