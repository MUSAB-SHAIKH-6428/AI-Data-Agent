# Ola AI Data Agent

Building an end-to-end AI Data Agent system to handle analytics and data operations on an Ola rides database. Instead of just sending a raw prompt to an LLM and hoping for the best, we break the system down into specialized sub-agents with strict guards, live database context, and an automated router.

## System Architecture

Here is the complete hierarchy:

```text
                           +------------------------+
                           |   User / Stakeholder   |
                           +-----------+------------+
                                       |
                                       v
                           +------------------------+
                           |       Data Agent       |
                           |     (Router Node)      |
                           +-----+------------+-----+
                                 |            |
          [SQL / Database Query] |            | [ELT / API / File Transform]
                                 v            v
                     +----------------+  +----------------+
                     |  SQL Analyst   |  |  ELT Analyst   |
                     | (Stateful DAG) |  | (ReAct Agent)  |
                     +-------+--------+  +-------+--------+
                             |                   |
                             v                   v
                       PostgreSQL DB        REST APIs &
                       (Ola Ride DB)        Data Storage
```

---

## 1. Main Data Agent (The Router)

The **Data Agent** (`agents/data_agent.py`) is the entry point. It reads the user request and uses Gemini structured output (`RouterSchema`) to classify the task as either `"sql"` or `"etl"`. It then delegates the question to the right sub-agent and returns the final answer.

![Data Agent Graph](data_agent_graph.png)

### How It Works
1. **`router_node`**: Inspects `state.messages[-1]`, prompts Gemini with `RouterSchema`, and stores the classification (`"sql"` or `"etl"`) in `state.route_response`.
2. **`route_edge`**: Conditional edge that forwards execution to either `sql_node` or `etl_node`.
3. **`sql_node`**: Builds the input payload, invokes the compiled `sql_analyst`, and collects the final response.
4. **`etl_node`**: Dispatches the request to the compiled `etl_analyst` ReAct agent and collects the execution summary.

---

## 2. SQL Analyst Agent

The **SQL Analyst** (`agents/sql_analyst.py`) takes a natural language question, pulls the live database schema from PostgreSQL, generates the query with safeguards, verifies safety with an AI judge, executes it, and returns a plain English summary.

![SQL Analyst Graph](sql_analyst_graph.png)

### Execution Pipeline
1. **`curate_ques`**: Cleans and refines the user's raw input into a clear business question.
2. **`prompt_query_context`**: Queries Postgres `information_schema` at runtime to inject table names, column types, and sample rows into the prompt so the LLM doesn't hallucinate table structures.
3. **`generate_sql`**: Generates a clean Postgres query with a default `LIMIT 10` guardrail.
4. **`is_safe_sql` (AI Judge)**: Inspects the generated SQL using `JudgeSchema`. Only `SELECT` statements are permitted. Destructive commands (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `TRUNCATE`) are marked unsafe.
5. **Branching**:
   - **Safe (`Yes`)** -> Proceeds to `execute_sql` via `psycopg2` and passes the query output to `represent_final_answer`.
   - **Unsafe (`No`)** -> Diverts to `canceled_sql` and explains why the query was rejected without touching Postgres.
6. **`represent_final_answer`**: Translates the raw SQL query results into a clear, non-technical response for the user.

---

## 3. ELT Analyst Agent

The **ELT Analyst** (`agents/etl_analyst.py`) is built as a ReAct loop. The model acts as a Python Data Analyst equipped with dedicated tools to fetch data from APIs and run Pandas transformations.

![ELT Analyst Graph](etl_analyst_graph.png)

### How It Works
1. **`llm_node`**: Evaluates chat history and decides whether a tool is required or if it can provide the final answer.
2. **`tool_node`**: Executes the requested tool and passes observation output back to the model:
   - **`extract_load_tool`**: Fetches data from an external REST API endpoint and saves it to disk (`csv`, `json`, or `parquet`).
   - **`transform_load_tool`**: Reads the top sample rows of a file, prompts the model to write the required Pandas transformation code, and executes it via `ELTTools.execute_code`.
3. **Loop**: Runs until the tool operations finish, then returns the final message to the user.

---

## Verified Test Cases

### Test Case 1: SQL Route (Database Query)
```python
response = data_agent.invoke({
    "messages": [HumanMessage(content="What are the different types of Payment Methods we have in our database?")],
    "route_response": ""
})
```
* **Router Decision:** `"sql"`
* **Generated SQL:**
  ```sql
  SELECT payment_method, COUNT(*) AS transaction_count
  FROM payments
  GROUP BY payment_method
  ORDER BY transaction_count DESC
  LIMIT 10;
  ```
* **Execution Output:**
  ```text
  [('google_pay', 3317), ('apple_pay', 3301), ('paypal', 3215), ('debit_card', 3138), ('credit_card', 3102)]
  ```
* **Final Response:** Friendly breakdown explaining that the database supports Google Pay, Apple Pay, PayPal, Debit Card, and Credit Card, along with their transaction counts.

---

### Test Case 2: ELT Route (API Extraction & Loading)
```python
response = data_agent.invoke({
    "messages": [HumanMessage(content="I want to extract the data from the API endpoint 'https://pokeapi.co/api/v2/pokemon' and save it to data/extract folder in the csv folder")],
    "route_response": ""
})
```
* **Router Decision:** `"etl"`
* **Tool Triggered:** `extract_load_tool`
* **Execution Output:**
  ```text
  Data successfully extracted and saved to C:\Users\MUSAB\Desktop\AI-Data-Agent\data\extract\extracted_data.csv
  ```
* **Final Response:** Confirms data was extracted and saved in CSV format at the requested directory.

---

### Test Case 3: SQL Security Guardrail (Blocking Unsafe Query)
```python
response = data_agent.invoke({
    "messages": [HumanMessage(content="Delete all cancelled rides from the rides table")],
    "route_response": ""
})
```
* **Router Decision:** `"sql"`
* **Generated SQL:** `DELETE FROM rides WHERE status = 'cancelled';`
* **Judge Decision:** `answer: "No"`, `comments: "Contains destructive DELETE command."`
* **Branching:** Diverts to `canceled_sql`.
* **Final Response:** *"The generated SQL query was deemed unsafe to execute. The reason provided by the judge is: Contains destructive DELETE command. Therefore, the SQL query will not be executed."* (Database remains untouched).

---

## Project Structure

```text
AI-Data-Agent/
├── Model/
│   └── Schema.py            # Pydantic schemas for states, router & judge
├── agents/
│   ├── data_agent.py        # Top-level Router agent (Working!)
│   ├── sql_analyst.py       # SQL Analyst LangGraph pipeline (Working!)
│   └── etl_analyst.py       # ELT Analyst ReAct agent (Working!)
├── utils/
│   ├── database.py          # Postgres connection & query execution
│   ├── elt_tools.py         # API extraction, normalization & code execution
│   └── llm_pick.py          # Helper to pick Gemini models (low/med/high)
├── data/                    # Sample datasets (users, rides, payments, etc.)
├── feed_db.py               # Loads CSV datasets into PostgreSQL
├── data_agent_graph.png     # Visual DAG of Data Agent Router
├── sql_analyst_graph.png    # Visual DAG of SQL Analyst
├── etl_analyst_graph.png    # Visual DAG of ELT Analyst
└── README.md
```

---

## Quick Setup & Running

1. **Install dependencies**
   ```bash
   uv sync
   # or
   # pip install -r requirements.txt
   ```

2. **Configure `.env`**
   ```env
   GEMINI_API_KEY=your_key_here
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=ola_db
   DB_USER=postgres
   DB_PASSWORD=your_password
   ```

3. **Run the Full System (Router Agent)**
   ```bash
   python agents/data_agent.py
   ```

4. **Run Individual Agents Directly**
   ```bash
   # Test SQL Analyst only
   python agents/sql_analyst.py

   # Test ELT Analyst only
   python agents/etl_analyst.py
   ```