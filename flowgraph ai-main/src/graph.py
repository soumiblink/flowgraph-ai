import sqlite3
from groq import Groq
import os
import re

# ✅ Load API key from Streamlit Secrets
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found. Please set it in Streamlit Secrets.")

client = Groq(api_key=api_key)

# ✅ Correct DB path (works locally + Streamlit Cloud)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")


# ✅ Run SQL on DB
def run_query(sql):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    conn.close()
    return result


# ✅ LLM → SQL
def generate_sql(query):
    prompt = f"""
You are an expert SQL generator for a business analytics system.

Database Tables and Relationships:

1. sales_order_headers (salesOrder, soldToParty, totalNetAmount, transactionCurrency, creationDate)
2. sales_order_items (salesOrder, salesOrderItem, material, netAmount, requestedQuantity)
3. outbound_delivery_items (deliveryDocument, referenceSdDocument, referenceSdDocumentItem)
4. outbound_delivery_headers (deliveryDocument)
5. billing_document_items (billingDocument, referenceSdDocument, material, netAmount)
6. billing_document_headers (billingDocument, accountingDocument, totalNetAmount, soldToParty)
7. payments_accounts_receivable (accountingDocument, amountInTransactionCurrency, customer)
8. business_partners (businessPartner)
9. products (product)

Relationships:
- sales_order_headers → sales_order_items via salesOrder
- sales_order_items → outbound_delivery_items via salesOrder + salesOrderItem
- outbound_delivery_items → billing_document_items via referenceSdDocument
- billing_document_items → billing_document_headers via billingDocument
- billing_document_headers → payments_accounts_receivable via accountingDocument

SQL Rules:
- Use JOINs properly based on relationships above
- Do NOT invent column names
- Return ONLY the SQL statement, no explanation
- Use GROUP BY when aggregating data
- Use SUM() for revenue or quantity calculations
- Use ORDER BY ... DESC for ranking queries
- Use LIMIT 10 for top-N results unless user specifies otherwise
- Use COUNT() for frequency or volume queries

User Query:
{query}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    sql = response.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()

    print("Generated SQL:", sql)
    return sql


# ✅ Safe SQL execution
def safe_run_query(sql):
    try:
        return run_query(sql)
    except Exception as e:
        print("SQL ERROR:", e)
        return f"Query failed: {str(e)}"


# ✅ Format raw SQL result
def format_result(result):
    if not result:
        return "No data found."
    return "\n".join(str(row) for row in result)


# ✅ Convert SQL result → nice answer
def generate_answer(query, result):
    formatted = format_result(result)

    prompt = f"""User asked:
{query}

SQL Result:
{formatted}

Instructions:
- Convert into a clear, structured answer
- Use bullet points or numbered list
- Highlight key values (order id, amount, customer)
- Keep it concise
- Do not include unnecessary text
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()


# ✅ Explain result in business terms
def explain_result(query, result):
    prompt = f"""User Query: {query}
SQL Result: {result}
Explain this result in simple business terms. Keep it short and clear."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()


# ✅ Extract order ID (for graph highlight)
def extract_order_id(query):
    match = re.search(r'\d{{5,}}', query)
    return match.group(0) if match else None


# ✅ Guardrails
def is_valid_query(query):
    keywords = ["order", "delivery", "billing", "payment", "product", "customer"]
    return any(k in query.lower() for k in keywords)


# ✅ MAIN FUNCTION (called by UI)
def app(query):
    if not is_valid_query(query):
        return {
            "sql": "",
            "result": "This system is designed to answer questions related to sales, deliveries, billing, and payments only.",
            "explanation": ""
        }

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

    return {
        "sql": sql,
        "result": answer,
        "explanation": explanation
    }