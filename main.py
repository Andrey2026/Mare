"""MARE — Metadata Agent with ReAct and rEtrieval.

Entry point: initializes DWH, runs Ingestion Agent demo,
executes scenarios with Assistant Agent, evaluates metrics.
"""

import asyncio
import json
import logging
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient

import config
from connectors.dwh import DWHConnector
from connectors.vector_store import VectorStoreConnector
from evaluation.ragas_metrics import evaluate_ragas
from evaluation.report import generate_report
from evaluation.search_metrics import evaluate_search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

PRECOMPUTED_DESCRIPTIONS = {
    "stg_contract_events": (
        "Staging table containing raw contract events loaded from source systems "
        "(crm_v2, billing). Each row represents a single event such as activation, "
        "termination, renewal, amendment, or payment. Includes contract_id, event_date, "
        "event_type, and monetary amount. This is the landing zone before deduplication "
        "and transformation into fact_contract_events. May contain duplicate events "
        "from different source systems. Related ETL: etl_load_stg_contract_events."
    ),
    "dim_contract": (
        "Dimension table for contracts. Contains contract master data: client name, "
        "contract status (active/terminated), assigned manager (manager_id FK to "
        "dim_manager), start and end dates, contract type (service/license). "
        "Business terms: agreement, deal, contract termination. "
        "Used in analytical queries about revenue by contract status and manager."
    ),
    "dim_manager": (
        "Dimension table for managers. Contains manager name and department "
        "(Sales, Enterprise). Referenced by dim_contract.manager_id. "
        "Used for grouping revenue and contract data by responsible manager. "
        "Business terms: account manager, sales representative."
    ),
    "dim_date": (
        "Calendar dimension table with date_id as surrogate key (format YYYYMMDD). "
        "Contains full_date, year, month, quarter, month_name. Referenced by "
        "fact_revenue.date_id and fact_contract_events.event_date_id. "
        "Used for time-based aggregation: by month, quarter, year."
    ),
    "fact_revenue": (
        "Fact table containing revenue records. Each row is a revenue entry tied to "
        "a contract (contract_id FK to dim_contract) and time period (date_id FK to "
        "dim_date). Includes amount and revenue_type (monthly/final). "
        "Business terms: revenue, income, billing amount. "
        "Key table for analytical queries about revenue by contract, manager, time period."
    ),
    "fact_contract_events": (
        "Fact table containing deduplicated contract lifecycle events. Transformed from "
        "stg_contract_events. Each row is an event (termination, renewal, activation) "
        "tied to a contract and date. Includes event_type and amount. "
        "Business terms: contract event, lifecycle, termination event. "
        "Related ETL: etl_transform_fact_contract_events (source: stg_contract_events)."
    ),
}

DM_CONTRACT_REPORT_DDL = """
CREATE TABLE IF NOT EXISTS dm_contract_report (
    report_id INTEGER PRIMARY KEY,
    contract_id INTEGER,
    client_name VARCHAR(100),
    manager_name VARCHAR(100),
    contract_status VARCHAR(20),
    total_revenue DECIMAL(15,2),
    event_count INTEGER,
    last_event_date DATE,
    report_month INTEGER,
    report_year INTEGER
);
"""


async def run() -> None:
    """Main execution flow."""
    logger.info("=" * 60)
    logger.info("MARE — Metadata Agent with ReAct and rEtrieval")
    logger.info("=" * 60)

    # --- Phase 1: Initialize DWH ---
    logger.info("\n--- Phase 1: Initializing DWH ---")
    dwh = DWHConnector()
    dwh.init_from_files()
    table_count = dwh.execute(
        "SELECT count(*) as cnt FROM sqlite_master WHERE type='table'"
    )
    logger.info("DWH initialized with %d tables", table_count[0]["cnt"])

    # --- Phase 2: Load pre-computed embeddings ---
    logger.info("\n--- Phase 2: Loading semantic layer ---")
    vs = VectorStoreConnector()
    for table_name, description in PRECOMPUTED_DESCRIPTIONS.items():
        vs.upsert(table_name, description, metadata={"source": "precomputed"})
    logger.info(
        "Loaded %d pre-computed descriptions into vector store", vs.count()
    )

    # --- Phase 3: Ingestion Agent demo ---
    logger.info("\n--- Phase 3: Ingestion Agent Demo ---")
    logger.info("Adding table dm_contract_report to DWH...")
    dwh.execute_script(DM_CONTRACT_REPORT_DDL)
    logger.info(
        "Table dm_contract_report created. Running Ingestion Agent..."
    )

    mcp_server_command = [sys.executable, "-m", "mcp_server"]
    mcp_client = MultiServerMCPClient(
        {
            "dwh-tools": {
                "command": mcp_server_command[0],
                "args": mcp_server_command[1:],
                "transport": "stdio",
            }
        }
    )

    from ingestion_agent.agent import run_ingestion

    ingestion_result = await run_ingestion(
        "dm_contract_report", mcp_client, vs
    )
    logger.info(
        "Ingestion Agent generated description (%d chars)",
        len(ingestion_result["description"]),
    )
    logger.info("Vector store now has %d entries", vs.count())

    # --- Phase 4: Assistant Agent scenarios ---
    logger.info("\n--- Phase 4: Running scenarios ---")
    gt = json.loads(config.GROUND_TRUTH_PATH.read_text())
    scenario_results = []

    from assistant_agent.agent import run_assistant

    for scenario in gt["scenarios"]:
        logger.info("\nScenario: %s", scenario["id"])
        logger.info("Question: %s", scenario["question"])

        result = await run_assistant(
            scenario["question"], mcp_client, vs
        )
        scenario_results.append(result)

        logger.info(
            "Answer (%d chars, %.1fs):",
            len(result["answer"]),
            result["duration_seconds"],
        )
        logger.info(result["answer"])

    # --- Phase 5: Evaluation ---
    logger.info("\n--- Phase 5: Evaluation ---")

    search_metrics = evaluate_search(vs, config.GROUND_TRUTH_PATH)
    ragas_metrics = evaluate_ragas(scenario_results, config.GROUND_TRUTH_PATH)
    generate_report(search_metrics, ragas_metrics, scenario_results)

    logger.info("\n" + "=" * 60)
    logger.info("Done. Results saved to %s", config.RESULTS_DIR)
    logger.info("=" * 60)

    dwh.close()


def main() -> None:
    """Entry point."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
