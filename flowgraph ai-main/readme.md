# FlowGraph AI

An LLM-powered business data query system with interactive graph visualization, built on top of SAP Order-to-Cash (O2C) data.

---

## Overview

Enterprise business data is often fragmented across multiple systems — sales orders, deliveries, billing documents, and payments rarely live in one place or speak the same language. Analysts spend hours tracing a single order through the full fulfillment cycle.

**FlowGraph AI** solves this by:
- Loading all O2C entities into a unified SQLite database
- Letting users query it in plain English via an LLM-powered interface
- Visualizing the full business flow as an interactive, data-backed graph

---

## Features

- **Graph-based data modeling** — relationships between orders, deliveries, billing, and payments modeled as a directed graph
- **Natural language queries** — ask questions in plain English; the LLM generates and executes the SQL
- **Data-backed responses** — answers are grounded in real database results, not hallucinations
- **Interactive graph visualization** — PyVis-powered graph rendered directly in the UI
- **Query-based highlighting** — mention a specific order ID and the graph filters to show only its flow
- **Domain guardrails** — off-topic queries are rejected before hitting the LLM

---

## Architecture

| Layer     | Technology        |
|-----------|-------------------|
| Frontend  | Streamlit         |
| Backend   | Python            |
| Database  | SQLite            |
| LLM       | Groq API (llama-3.3-70b-versatile) |

### Query Flow

```
User Query
   → Guardrail check
   → LLM generates SQL
   → SQLite executes query
   → Raw result returned
   → LLM formats natural language answer
   → Displayed in UI
```

### Architecture Decisions

**Why Streamlit?**
Streamlit lets you build a functional data app in pure Python with no frontend code. For a project focused on data querying and visualization, it removes all UI boilerplate and keeps the codebase minimal and readable.

**Why SQLite?**
The dataset is a static, read-only SAP O2C export loaded once at startup. SQLite is zero-config, file-based, and ships with Python — no server, no credentials, no connection pooling needed. For a dataset of this size (~thousands of rows across 19 tables), it performs well and keeps the stack simple. A production system would swap this for PostgreSQL or a data warehouse, but SQLite is the right choice here for portability and ease of setup.

**Why Groq?**
Groq's LPU inference delivers very low latency on large models. Using `llama-3.3-70b-versatile` gives strong SQL generation quality at speeds that feel responsive in a Streamlit UI. The API is OpenAI-compatible, making it easy to swap models or providers if needed.

**Why NetworkX + PyVis?**
NetworkX handles graph construction and relationship traversal in Python. PyVis converts it to an interactive HTML/JavaScript visualization using vis.js under the hood. This combination avoids a separate frontend framework while still producing a fully interactive, physics-enabled graph embedded directly in Streamlit via `components.html()`.

---

## Database Design

The raw dataset is a collection of JSONL files organized into folders by entity type under `data/sap-o2c-data/`. The loader (`src/load_data.py`) scans each folder, concatenates all `part-*.jsonl` files, serializes any nested JSON columns to strings, and writes each entity as a table in `data.db`.

Key tables and their roles:

| Table | Description |
|-------|-------------|
| `sales_order_headers` | Root of the O2C flow — one row per sales order |
| `sales_order_items` | Line items per order |
| `outbound_delivery_items` | Links orders to physical deliveries |
| `billing_document_headers` | Invoice records linked to deliveries |
| `payments_accounts_receivable` | Payment records linked to billing documents |
| `business_partners` | Customer master data |
| `products` | Product catalog |

Foreign key chain used for graph traversal:
```
salesOrder → referenceSdDocument → deliveryDocument → billingDocument → accountingDocument
```

---

## LLM Prompting Strategy

SQL generation uses a single-shot prompt with four components:

1. **Role definition** — tells the model it is a SQL generator for a specific business analytics system, not a general assistant
2. **Schema context** — lists all tables with their relevant columns so the model never has to guess column names
3. **Relationship map** — explicitly states the JOIN paths between tables, preventing the model from inventing incorrect joins
4. **SQL rules** — instructs the model to use `GROUP BY` for aggregation, `SUM()` for revenue, `ORDER BY DESC` for ranking, `LIMIT 10` for top-N queries, and to return only the SQL with no explanation or markdown

A concrete example query/SQL pair is included in the prompt to anchor the model's output format for analytics queries.

After the LLM responds, the SQL is cleaned with:
```python
sql.replace("```sql", "").replace("```", "").strip()
```
This strips any markdown fences the model may include despite being told not to.

A second LLM call then takes the original query + raw SQL result and produces a structured, bullet-pointed business answer. A third call generates a short plain-English explanation of what the result means in business terms.

---

## Graph Model

The O2C business flow is modeled as a directed graph:

```
Customer → Sales Order → Delivery → Billing Document → Payment
```

Each node represents a real entity from the database. Edges represent foreign key relationships:

- `sales_order_headers.salesOrder` → `outbound_delivery_items.referenceSdDocument`
- `outbound_delivery_items.deliveryDocument` → `billing_document_items.referenceSdDocument`
- `billing_document_items.billingDocument` → `billing_document_headers.billingDocument`
- `billing_document_headers.accountingDocument` → `payments_accounts_receivable.accountingDocument`

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/your-username/flowgraph-ai.git
cd "flowgraph ai-main"
```

### 2. Create a virtual environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install streamlit groq python-dotenv pandas networkx pyvis
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
```

### 5. Load data into SQLite

```bash
python src/load_data.py
```

This scans `data/sap-o2c-data/` for all JSONL files and loads them into `data.db`.

### 6. Run the app

```bash
streamlit run src/ui.py
```

---

## Example Queries

```
Which products are associated with the highest number of billing documents?
```
```
Show the full flow for sales order 740506
```
```
Which sales orders have a delivery but no billing document?
```
```
List the top 5 customers by total net amount
```
```
Find orders where payment has not been received
```

---

## Guardrails

Queries are validated before reaching the LLM. Only questions related to:

> orders, deliveries, billing, payments, products, customers

...are processed. Everything else returns:

> "This system is designed to answer questions related to sales, deliveries, billing, and payments only."

This check runs entirely in Python before any API call is made, so off-topic queries cost nothing and return instantly.

Three additional layers of error handling sit below the guardrail:

- **SQL execution errors** — caught by `safe_run_query()`, returned as a clean `"Query failed: ..."` message without exposing a traceback
- **Empty results** — detected before the answer LLM call; returns `"No data found for this query."` immediately
- **Markdown in SQL** — stripped unconditionally after every LLM response to prevent syntax errors from backtick-wrapped output

---

## AI Usage

This project was built with the assistance of AI coding tools throughout development:

- **Kiro / Cursor** — used for iterative code generation, refactoring, and debugging across all source files. Prompts were written step-by-step, with each output reviewed and corrected before moving to the next task.
- **Groq API (LLaMA 3.3)** — powers the natural language → SQL generation and result summarization at runtime.
- **Iterative prompting** — the LLM prompt for SQL generation was refined multiple times to handle JOIN logic, column naming, and result limits correctly.
- **Debugging with AI** — error tracebacks (e.g., SQLite type errors, decommissioned model IDs) were resolved by feeding errors back into the AI assistant for targeted fixes.

---

## Demo Instructions

### Using the chat interface

1. Type a natural language question into the text area
2. Click **Run**
3. The system generates SQL, queries the database, and returns a structured answer

### Viewing the full graph

1. Scroll to the graph section
2. Click **Show Business Flow Graph**
3. The full O2C flow graph renders inline with color-coded nodes:
   - Blue = Sales Orders
   - Orange = Deliveries
   - Green = Billing Documents
   - Red = Payments

### Highlighting a specific order flow

1. Type a query mentioning a specific order ID (e.g., `Show flow for sales order 740506`)
2. Click **Show Graph for this Query**
3. The graph filters to show only the nodes and edges connected to that order

---

## Project Structure

```
flowgraph ai-main/
├── src/
│   ├── graph.py              # LLM → SQL pipeline + guardrails
│   ├── graph_visualizer.py   # NetworkX + PyVis graph builder
│   ├── load_data.py          # JSONL → SQLite data loader
│   └── ui.py                 # Streamlit frontend
├── data/
│   └── sap-o2c-data/         # Raw JSONL dataset (O2C entities)
├── data.db                   # Generated SQLite database
├── graph.html                # Generated graph visualization
└── .env                      # API keys (not committed)
```
