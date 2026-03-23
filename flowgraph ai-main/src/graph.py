import sqlite3
from groq import Groq
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ✅ Run SQL on DB
def run_query(sql):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    conn.close()
    return result


# ✅ LLM → SQL (PUT YOUR PROMPT HERE)
def generate_sql(query):
    prompt = f"""
You are an expert SQL generator.

Database Tables and Relationships:

1. sales_order_headers (salesOrder, soldToParty, totalNetAmount)
2. sales_order_items (salesOrder, salesOrderItem, material)
3. outbound_delivery_items (deliveryDocument, referenceSdDocument, referenceSdDocumentItem)
4. outbound_delivery_headers (deliveryDocument)
5. billing_document_items (billingDocument, referenceSdDocument, material)
6. billing_document_headers (billingDocument, accountingDocument, totalNetAmount)
7. payments_accounts_receivable (accountingDocument, amountInTransactionCurrency)
8. business_partners (businessPartner)
9. products (product)

Relationships:
- sales_order_headers → sales_order_items via salesOrder
- sales_order_items → outbound_delivery_items via salesOrder + item
- outbound_delivery_items → billing_document_items via referenceSdDocument
- billing_document_items → billing_document_headers via billingDocument
- billing_document_headers → payments via accountingDocument

Rules:
- Use JOINs properly
- Do NOT invent columns
- Return ONLY SQL
- Limit results to 10 rows unless specified

User Query:
{query}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    sql = response.choices[0].message.content.strip()
    if "```" in sql:
        sql = sql.replace("```sql", "").replace("```", "").strip()
    print("Generated SQL:", sql)
    return sql


def format_result(result):
    if not result:
        return "No data found."
    return "\n".join(str(row) for row in result)


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
- Do not include unnecessary text"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


# ✅ Guardrails
def is_valid_query(query):
    keywords = ["order", "delivery", "billing", "payment", "product", "customer"]
    return any(k in query.lower() for k in keywords)


# ✅ MAIN FUNCTION (UI CALLS THIS)
def app(query):
    if not is_valid_query(query):
        return "This system is designed to answer questions related to sales, deliveries, billing, and payments only."

    sql = generate_sql(query)

    try:
        result = run_query(sql)
        return generate_answer(query, result)
    except Exception as e:
        return f"Error executing SQL: {e}"


print("Response formatting improved")