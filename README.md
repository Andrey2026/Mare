# MARE — Metadata Agent with ReAct and rEtrieval

Proof-of-concept implementation of the two-loop metadata agent architecture described in:

> **A ReAct and RAG-Based Framework for Metadata Generation and Access in Relational Data Warehouse Processes**
> A. Martynov, M. Lapina, M. Babenko — Big Data and Cognitive Computing (BDCC), MDPI

## Quick Start

```bash
git clone https://github.com/Andrey2026/Mare.git
cd mare
cp .env.example .env       # configure LLM API key (see below)
uv sync                    # install dependencies
uv run python main.py      # run the full pipeline
```

Results are saved to `results/metrics.json` and `results/report.md`.

## LLM Configuration

The project uses any **OpenAI-compatible API**. Configure three variables in `.env`:

```
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1    # or proxy URL
LLM_MODEL=gpt-4o-mini
```

### Model Requirements

The LLM must support **function calling** (tool use). The agent relies on multi-step ReAct loops where the LLM autonomously decides which tools to call and in what order.

**Tested models:** `gpt-4o-mini` (default, recommended), `gpt-4o`.

**Embeddings** use the same OpenAI-compatible API (model `text-embedding-3-small` by default).

## Architecture

Two-loop system with a shared semantic layer:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Ingestion Agent │────>│   LanceDB        │<────│ Assistant Agent │
│ (ReAct + LLM)   │     │ (Semantic Layer) │     │ (ReAct + LLM)  │
└────────┬────────┘     └──────────────────┘     └────────┬───────┘
         │                                                │
         │              ┌──────────────────┐              │
         └─────────────>│   MCP Server     │<─────────────┘
                        │ (stdio, 6 tools) │
                        └────────┬─────────┘
                                 │
                        ┌────────┴─────────┐
                        │  SQLite (DWH)    │
                        └──────────────────┘
```

- **Ingestion Agent** — analyzes DDL and ETL context via MCP tools, generates semantic descriptions using LLM, stores in vector DB
- **Assistant Agent** — answers user questions by combining RAG search (LanceDB) with MCP diagnostic tools
- **MCP Server** — provides 6 tools for accessing external systems (DWH structure, ETL processes, logs)
- **LanceDB** — embedded vector database for semantic search

The LLM autonomously decides which tools to call using the ReAct pattern (Reasoning + Acting). There is no hardcoded sequence of tool calls — the agent plans each step based on the question and results of previous steps.

## Pipeline: What Happens When You Run It

### Phase 1: DWH Initialization (~1 sec)

Creates SQLite database `data/dwh.db` with 9 tables organized by DWH layers (see [ER diagram](docs/dwh_schema.drawio)):
- **Staging:** `stg_contract_events` (raw events from source systems)
- **Dimension:** `dim_contract`, `dim_manager`, `dim_date`
- **Fact:** `fact_revenue`, `fact_contract_events`
- **ETL metadata:** `etl_processes`, `etl_execution_log`, `etl_process_logs`

Test data includes 5 contracts, 12 revenue records, ETL execution history with a deliberately anomalous run on the last day (for Scenario 2).

### Phase 2: Semantic Layer Loading (~3 sec)

Pre-written descriptions of 6 tables are vectorized via OpenAI embeddings API and loaded into LanceDB. These descriptions contain business terms and synonyms enabling semantic search.

### Phase 3: Ingestion Agent Demo (~5-10 sec)

Demonstrates the Ingestion loop from the paper:
1. A new table `dm_contract_report` is added to the DWH
2. Ingestion Agent detects it and autonomously:
   - Calls `get_table_schema` to retrieve the DDL
   - Calls `find_etl_process_by_table` to find related ETL processes
   - LLM synthesizes a semantic description from DDL + ETL context
3. The description is vectorized and stored in LanceDB

After this phase, the vector store has 7 entries — ready for Assistant Agent queries.

### Phase 4: Scenarios (~20-40 sec)

The Assistant Agent receives a question and autonomously decides which tools to use and in what order using the ReAct pattern.

**Scenario 1: Analytical Query**

- *Question:* "Write a query returning revenue from terminated contracts for 2025, by month and responsible managers"
- *Available data:* `dim_contract` (contract status), `fact_revenue` (amounts), `dim_manager` (names), `dim_date` (periods)
- *Available tools:* `search_vector_store`, `get_table_schema`, `analyze_query_plan`
- *Expected result:* A valid SQL query with explanation of tables used and filters applied

**Scenario 2: ETL Diagnostics**

- *Question:* "Why is the contract report mart loading taking twice as long today?"
- *Available data:* ETL execution history with an anomalous run (1967s vs ~912s average), logs with warnings about hash join fallback and 3.5x data growth in source table
- *Available tools:* `search_vector_store`, `find_etl_process_by_table`, `get_process_execution_status`, `fetch_recent_logs`, `get_table_increment_stats`, `analyze_query_plan`
- *Expected result:* Root cause diagnosis with evidence and recommendations

### Phase 5: Evaluation (~30-60 sec)

Computes RAGAS metrics, semantic search quality, and execution time. Saves results to `results/`.

## Results and How to Interpret Them

Results are saved in two files:

- **`results/report.md`** — Markdown report with tables (open in IDE with preview)
- **`results/metrics.json`** — same data in machine-readable format

### RAGAS Metrics

| Metric | What it measures | Good if |
|--------|-----------------|---------|
| **Faithfulness** | Is the answer grounded in tool results and retrieved context, not LLM hallucinations? | > 0.7 |
| **Answer Relevance** | Does the answer actually address the question asked? | > 0.7 |
| **Context Precision** | Are the retrieved documents relevant to the question? | > 0.5 |
| **Context Recall** | Were all necessary documents/data retrieved? | > 0.7 |

Note: metrics may vary between runs due to LLM non-determinism. This is expected.

### Semantic Search Precision/Recall

| Metric | What it measures |
|--------|-----------------|
| **Precision@k** | Out of k retrieved tables, how many are relevant. P@3 = 0.333 means 1 out of 3 (expected when searching for 1 table). |
| **Recall@k** | Was the target table found in top-k results? R@3 = 1.000 means yes, always found. |

### Execution Time

Compares agent response time with expert estimates of manual work:
- Scenario 1: manual search ~15 minutes
- Scenario 2: manual diagnostics ~30 minutes

## Project Structure

```
mare/
├── config.py              # All settings with env overrides
├── main.py                # Entry point (full pipeline)
│
├── connectors/            # Connectors to external systems
│   ├── dwh.py             # SQLite connection and query execution
│   ├── vector_store.py    # LanceDB: upsert, search (used by agents directly)
│   └── llm.py             # LLM factory (OpenAI-compatible)
│
├── ingestion_agent/       # Ingestion Agent (ReAct + MCP tools)
│   ├── agent.py           # LangGraph ReAct graph
│   └── prompts.py         # System prompt for description generation
│
├── assistant_agent/       # Assistant Agent (ReAct + MCP tools + RAG)
│   ├── agent.py           # LangGraph ReAct graph with search tool
│   └── prompts.py         # System prompt for Q&A
│
├── mcp_server/            # MCP server with 6 diagnostic tools
│   ├── server.py          # Entry point (stdio transport)
│   ├── dwh_tools.py       # get_table_schema, analyze_query_plan
│   ├── etl_tools.py       # find_etl_process_by_table, get_process_execution_status
│   └── log_tools.py       # fetch_recent_logs, get_table_increment_stats
│
├── evaluation/            # Metrics and reporting
│   ├── ragas_metrics.py   # RAGAS: Faithfulness, Answer Relevance, Context Precision/Recall
│   ├── search_metrics.py  # Precision/Recall of semantic search
│   └── report.py          # Generate metrics.json and report.md
│
├── data/                  # Data files
│   ├── ddl/schema.sql     # DWH table definitions
│   ├── seed/seed.sql      # Test data
│   └── ground_truth.json  # Expected results for evaluation
│
└── results/               # Output (gitignored)
    ├── metrics.json
    └── report.md
```

### Key Design Principles

- **Connectors** (`connectors/`) provide only connection and query execution — no business logic
- **Vector store** is accessed directly by agents (internal system), while **DWH/ETL/logs** are accessed through the **MCP server** (external systems)
- **MCP tools** encapsulate business logic and SQL queries — agents never execute raw SQL
- Every `.py` file has an `if __name__ == "__main__":` block for standalone testing

## Requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) package manager
- OpenAI-compatible API key with function calling and embeddings support

## License

MIT
