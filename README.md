# Ola AI Data Agent

Building an AI Data Agent to handle questions and data operations on an Ola rides database. Instead of just dumping a prompt to an LLM and hoping for the best, we break the work down into specialized agents with proper guards, schema context, and validation.

---

## Where We Are Right Now 🎯

We have successfully built and tested two core sub-agents:
1. **SQL Analyst Agent** (`agents/sql_analyst.py`) - Queries the PostgreSQL database safely.
2. **ELT Analyst Agent** (`agents/etl_analyst.py`) - Extracts API data and runs Pandas transformations.

---

## 1. SQL Analyst Agent

It takes a user's natural language question, inspects the live PostgreSQL database schema, writes the SQL query, checks whether it's safe to run, executes it, and explains the result in simple terms.

Here is the compiled LangGraph workflow:

![SQL Analyst Graph](sql_analyst_graph.png)

### How the SQL Analyst Works (Step-by-Step)

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

## 2. ELT Analyst Agent

The **ELT Analyst Agent** is built as a ReAct loop. The LLM acts as a Python Data Analyst with access to custom ELT tools. It decides which tool to call based on the user's request, executes it, checks the output, and responds back.

Here is the compiled LangGraph workflow:

![ELT Analyst Graph](etl_analyst_graph.png)

### How the ELT Analyst Works

1. **`llm_node`**  
   Takes the user's prompt and chat history. The LLM has tools bound to it (`extract_load_tool` and `transform_load_tool`). If it needs to run an action, it outputs a tool call; otherwise, it provides the final answer and ends.

2. **`tool_node` & Tools**  
   Executes the requested tool and feeds the observation back to the LLM:
   - **`extract_load_tool`**: Hits an external API endpoint, fetches the data, and dumps it into the target folder in the requested format (`csv`, `json`, or `parquet`).
   - **`transform_load_tool`**: Reads sample rows from an existing file to understand its shape, prompts the LLM to generate the exact Pandas transformation code needed, runs that code in a clean execution environment, and saves the transformed file.

3. **Conditional Loop**:  
   If tools were called, the loop routes the result back to `llm_node` so the agent can confirm the task is complete or take next steps. If no more tools are needed, it finishes.

---

## Project Structure

```text
AI-Data-Agent/
├── Model/
│   └── Schema.py            # Pydantic schemas for agent states & judge
├── agents/
│   ├── sql_analyst.py       # SQL Analyst LangGraph workflow (Working!)
│   ├── etl_analyst.py       # ELT Analyst ReAct agent (Working!)
│   └── data_agent.py        # Main router agent (up next)
├── utils/
│   ├── database.py          # Postgres connection & query runner
│   ├── elt_tools.py         # ELT helper class (API extraction, code execution)
│   └── llm_pick.py          # Helper to pick Gemini models (low/med/high)
├── data/                    # Sample CSV datasets & extract output folders
├── feed_db.py               # Script to load CSV data into Postgres
├── sql_analyst_graph.png    # Mermaid graph of SQL Analyst
├── etl_analyst_graph.png    # Mermaid graph of ELT Analyst
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

4. **Run the ELT Analyst**
   ```bash
   python agents/etl_analyst.py
   ```

---

## What's Next 🚀

- **Main Data Agent (`agents/data_agent.py`)**: The top-level router node that takes any incoming user request and decides whether to send it to the **SQL Analyst** (for database questions) or the **ELT Analyst** (for API ingestion and data file transformations).