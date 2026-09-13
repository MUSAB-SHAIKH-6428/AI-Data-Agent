# Ola AI Data Agent

Building an AI Data Agent to handle questions and data operations on an Ola rides database. Instead of just dumping a prompt to an LLM and hoping for the best, we break the work down into specialized agents with proper guards, schema context, and validation.

---

## Where We Are Right Now: SQL Analyst Agent 🎯

We just finished building and testing the **SQL Analyst Agent** (`agents/sql_analyst.py`). 

It takes a user's question, inspects the live PostgreSQL database, writes the SQL query, checks whether it's safe to run, executes it, and explains the result in simple terms.

Here is the compiled LangGraph workflow:

![SQL Analyst Graph](sql_analyst_graph.png)

---

## How the SQL Analyst Works (Step-by-Step)

1. **`curate_ques`**
   Takes the raw user question and cleans it up into a clear, well-phrased business question using a light LLM.

2. **`prompt_query_context`**
   Connects to Postgres and pulls live schema details (table names, column names, data types, and sample rows) directly from `information_schema`. This gives the LLM the exact context so it doesn't hallucinate table or column names.

3. **`generate_sql`**
   Feeds the schema and curated question into the model to write the Postgres query. It defaults to a `LIMIT 10` safeguard so we don't accidentally dump thousands of rows.

4. **`is_safe_sql` (The Judge)**
   Before anything touches the database, a judge LLM evaluates the query using structured output (`JudgeSchema`). It checks if the query only reads data (`SELECT`). If there's any dangerous operation like `DROP`, `DELETE`, `UPDATE`, `INSERT`, or `TRUNCATE`, it flags it as unsafe (`No`).

5. **Branching**:
   - **Safe (`Yes`)** -> moves to `execute_sql`, runs the query with `psycopg2`, and passes the output to `represent_final_answer`.
   - **Unsafe (`No`)** -> moves to `canceled_sql`, stops execution, and explains why the query was rejected without touching the database.

6. **`represent_final_answer`**
   Takes the SQL execution result and user question, then writes a friendly, plain English summary of the findings.

---

## Project Structure

```text
AI-Data-Agent/
├── Model/
│   └── Schema.py            # Pydantic schemas for agent state & judge
├── agents/
│   ├── sql_analyst.py       # SQL Analyst LangGraph workflow (Working!)
│   ├── etl_analyst.py       # ETL agent (up next)
│   └── data_agent.py        # Main router agent (up next)
├── utils/
│   ├── database.py          # Postgres connection & query runner
│   └── llm_pick.py          # Helper to pick Gemini models (low/med/high)
├── data/                    # Sample CSV datasets (users, rides, payments, etc.)
├── feed_db.py               # Script to load CSV data into Postgres
├── sql_analyst_graph.png    # Mermaid graph export of the SQL agent
└── README.md
```

---

## Quick Setup & Running

1. **Setup environment & dependencies**
   ```bash
   uv sync
   # or with standard venv:
   # pip install -r requirements.txt
   ```

2. **Setup `.env`**
   ```env
   GEMINI_API_KEY=your_key_here
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=ola_db
   DB_USER=postgres
   DB_PASSWORD=your_password
   ```

3. **Run the SQL Analyst**
   ```bash
   python agents/sql_analyst.py
   ```

---

## What's Next 🚀

- **ETL Analyst Sub-Agent**: Tool-calling ReAct agent to handle file transformations, API calls, and data pipelines.
- **Main Data Agent**: The top-level router that takes any user request and decides whether to send it to the SQL Analyst or the ETL Analyst.