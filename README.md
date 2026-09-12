# 🏗️ System Architecture: Ola AI Data Agent

Rather than sending raw prompts directly to an LLM, the system routes natural-language business requests through specialized sub-agents with strict state boundaries, deterministic security checks, and targeted model tiering.

---

## 📐 High-Level Architecture

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
         [SQL / Database Query] |            | [ETL / API / File Transform]
                                v            v
                    +----------------+  +----------------+
                    |  SQL Analyst   |  |  ETL Analyst   |
                    | (Stateful DAG) |  | (ReAct Agent)  |
                    +-------+--------+  +-------+--------+
                            |                   |
                            v                   v
                      PostgreSQL DB        REST APIs &
                      (Ola Ride DB)        Data Storage
```

### Core Architecture Components 

1. Main and Decision Maker Data AGent
2. SQL Analyst Sub-Agent
## Execution PIPELINE : 
    curate_question: Cleans unformatted, informal prompts into crisp business queries.

    prompt_query_context (Context Engineering): Queries PostgreSQL's information_schema at runtime to extract live tables, column types, constraints, and 5 sample rows per table, eliminating hallucinations.

    generate_sql: Uses a specialized coding model tier to generate syntactically strict PostgreSQL queries with a mandatory row limit guardrail (LIMIT 10).

    is_safe (AI-as-a-Judge): Intercepts generated SQL prior to execution using JudgeSchema to enforce a read-only policy. Only SELECT statements are permitted; destructive commands (DROP, DELETE, UPDATE, INSERT) are flagged as unsafe.

    Branching:

    Safe (yes): Proceeds to execute_sql via psycopg2, executes against PostgreSQL, and passes output to represent_final_answer.

    Unsafe (no): Routes to cancelled_sql to return a clear justification without querying the database.

3. ETL Analyst Sub-Agent
    Design Pattern: Tool-Calling ReAct Loop (Reasoning + Acting).

    Role: Handles ad-hoc API ingestion, format conversions, and data cleaning/filtering pipelines.

    Execution Pipeline:

    Tool Binding: Binds atomic Python utilities (extract_load_tool, transform_load_tool) decorated with @tool to the LLM.

    Tool Execution: LLM inspects input paths, formats, and destinations, emitting a structured tool_call.

    Observation Feedback: The custom tool_node executes the respective Python function (requests, pandas, exec), wraps the execution log as a ToolMessage, and routes back to the LLM until the pipeline finishes.