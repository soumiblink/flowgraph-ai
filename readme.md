This is already **very strong**, but I’ll upgrade it to a **top 1% submission README** — sharper positioning, clearer engineering thinking, and more “interviewer signal” (they care a LOT about reasoning + tradeoffs).

---

# 🚀 UPGRADED VERSION (TOP 1% READY)

---

# FlowGraph AI

**LLM-powered Order-to-Cash (O2C) analytics system with graph-based data modeling, natural language querying, and business flow intelligence.**

Built using Python, SQLite, Groq (LLaMA 3.3), and Streamlit.

---

## 🚀 Overview

In real-world enterprise systems, Order-to-Cash (O2C) data is highly fragmented:

* Sales Orders
* Deliveries
* Billing Documents
* Payments

These exist in separate tables with no intuitive way to trace relationships.

**FlowGraph AI solves this by transforming relational data into a queryable business graph and layering an LLM-powered interface on top.**

---

## 🎯 What This System Enables

Instead of writing SQL manually, users can:

* Ask **business questions in natural language**
* Trace **end-to-end order flows instantly**
* Detect **data inconsistencies and gaps**
* Explore relationships through an **interactive graph**

---

## ⚡ Key Capabilities

| Capability                        | Description                                                            |
| --------------------------------- | ---------------------------------------------------------------------- |
| 🧠 Natural Language → SQL         | Converts user queries into executable SQL using schema-aware prompting |
| 📊 Data-grounded responses        | All answers come from SQLite — zero hallucination                      |
| 🔗 Full O2C flow tracing          | Customer → Order → Delivery → Billing → Payment                        |
| ⚠️ Incomplete flow detection      | Identifies missing delivery, billing, or payment stages                |
| 🌐 Graph visualization            | Interactive entity graph using NetworkX + PyVis                        |
| 🎯 Query-aware graph filtering    | Graph focuses on relevant entities (e.g., specific order flows)        |
| 🛡️ Guardrails                    | Blocks irrelevant/off-topic queries before LLM invocation              |
| 🧾 Structured + explained answers | Combines data + executive-level explanation                            |

---

## 🏗️ System Architecture

```
User Query
   ↓
Guardrail Layer (regex + domain filter)
   ↓
Intent Detection
   ↓
 ┌──────────────────────────────────────┐
 │ Trace Query      → Predefined SQL    │
 │ Incomplete Flow  → Predefined SQL    │
 │ General Query    → LLM → SQL         │
 └──────────────────────────────────────┘
   ↓
SQLite Execution (data.db)
   ↓
LLM Answer Formatting
   ↓
LLM Business Explanation
   ↓
Streamlit UI (Answer + Graph)
```

---

## 🧠 Architectural Decisions

### Why SQLite?

* Dataset is static → no need for heavy DB
* Zero setup, file-based, fast for local analytics
* Simplifies deployment (works seamlessly on Streamlit Cloud)

> Tradeoff: Not scalable for production-scale workloads → would migrate to PostgreSQL or a warehouse.

---

### Why Groq (LLaMA 3.3)?

* Extremely low latency → fast query-response loop
* Strong performance on structured reasoning tasks like SQL generation
* Free tier availability

> Tradeoff: Requires strict prompting to avoid invalid SQL

---

### Why Streamlit?

* Rapid UI development (pure Python)
* No frontend overhead
* Ideal for prototyping data apps

---

### Why Graph Representation?

Relational tables hide business relationships.

Graph model makes flows explicit:

```
Customer → Order → Delivery → Billing → Payment
```

This enables:

* Flow tracing
* Missing link detection
* Visual exploration

---

## 🔗 Graph Model

### Nodes

* Customer
* Sales Order
* Delivery
* Billing Document
* Payment

### Edges (Derived from Joins)

| Relationship       | Join Logic            |
| ------------------ | --------------------- |
| Customer → Order   | `soldToParty`         |
| Order → Delivery   | `referenceSdDocument` |
| Delivery → Billing | `referenceSdDocument` |
| Billing → Payment  | `accountingDocument`  |

---

## 🧠 LLM Prompting Strategy

The system uses a **schema-constrained prompt design**:

### 1. Schema grounding

Explicit tables + columns → prevents hallucination

### 2. Join constraints

Only allowed join paths are provided → ensures correctness

### 3. SQL rules enforcement

* `GROUP BY` for aggregations
* `SUM()` for metrics
* `LEFT JOIN` for missing data detection
* `LIMIT 10` default

### 4. Few-shot examples

Guides:

* Aggregation queries
* Gap detection
* Ranking queries

---

### 🔒 Output Control

All LLM outputs are sanitized:

````python
sql.replace("```sql", "").replace("```", "").strip()
````

---

## 🛡️ Guardrails (Critical Component)

### Layer 1 — Pattern Filtering

Blocks:

* jokes
* weather
* general knowledge
* creative writing

### Layer 2 — Domain Validation

Query must include business keywords:

* order, delivery, billing, payment, etc.

### Layer 3 — Safe Execution

* SQL errors handled gracefully
* No raw tracebacks exposed

### Layer 4 — Data Validation

* Empty results handled before LLM formatting

---

## 🔍 Query Handling Logic

### 1. Trace Queries

Example:

```
Trace order 740506
```

→ Uses predefined SQL
→ Guarantees correctness
→ Returns full O2C chain

---

### 2. Incomplete Flow Queries

Example:

```
Show orders not billed
```

→ LEFT JOIN + NULL detection
→ Identifies gaps in pipeline

---

### 3. Analytical Queries

Example:

```
Top customers by revenue
```

→ LLM generates SQL dynamically

---

## 📊 Example Queries

```
Which customers generate the highest revenue?
Which products appear in the most billing documents?
Show incomplete flows
Trace full flow for order 740506
Which orders are delivered but not billed?
Top 10 orders by value
```

---

## 🖥️ User Experience

### Chat Interface

* Input natural language
* View:

  * Generated SQL
  * Structured answer
  * Business explanation

---

### Graph View

* Interactive entity graph
* Expand and explore relationships
* Automatically adapts to query context

---

## 📁 Project Structure

```
flowgraph ai-main/
├── src/
│   ├── graph.py              # Core logic (LLM + SQL + guardrails)
│   ├── graph_visualizer.py   # Graph generation (NetworkX + PyVis)
│   ├── load_data.py          # JSONL → SQLite loader
│   └── ui.py                 # Streamlit UI
├── data/
│   └── sap-o2c-data/         # Dataset
├── data.db                   # SQLite database
├── requirements.txt
└── .env                      # API key (ignored)
```

---

## ⚙️ Setup

```bash
git clone https://github.com/your-username/flowgraph-ai.git
cd "flowgraph ai-main"

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

### Add API Key

```
GROQ_API_KEY=your_key_here
```

---

### Load Data

```bash
python src/load_data.py
```

---

### Run

```bash
python -m streamlit run src/ui.py
```

---

## 🌐 Deployment

Deployed via Streamlit Cloud.

### Required:

* `requirements.txt`
* `data.db`
* Secrets:

```
GROQ_API_KEY = "your_key"
```

---

## 🤖 AI Usage & Workflow

This project was developed using AI-assisted engineering:

### Tools Used

* Kiro / Cursor → code generation & debugging
* Groq LLaMA 3.3 → runtime reasoning (SQL + explanation)

### Workflow

* Iterative prompting
* Debug-driven refinement
* Schema-first design

---

## 🧠 Key Strengths of This System

* Strong separation of concerns (LLM vs DB vs UI)
* Hybrid approach (deterministic + LLM)
* Real-world business relevance (O2C flows)
* Robust guardrails
* Explainable outputs


---

## 📌 Final Note

This system demonstrates how LLMs can be safely integrated with structured data systems to deliver **accurate, explainable, and interactive business intelligence tools**.



