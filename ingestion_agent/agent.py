"""Ingestion Agent — LangGraph ReAct graph for metadata ingestion."""

import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from connectors.llm import get_llm
from connectors.vector_store import VectorStoreConnector
from ingestion_agent.prompts import INGESTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def run_ingestion(
    table_name: str,
    mcp_client: MultiServerMCPClient,
    vector_store: VectorStoreConnector,
) -> dict[str, Any]:
    """Run Ingestion Agent for a single table.

    Args:
        table_name: Name of the table to ingest.
        mcp_client: Connected MCP client with DWH tools.
        vector_store: Vector store connector for upserting descriptions.

    Returns:
        Dict with table_name, description, and message count.
    """
    llm = get_llm()
    tools = await mcp_client.get_tools()

    agent = create_react_agent(
        llm,
        tools,
        prompt=INGESTION_SYSTEM_PROMPT,
    )

    user_message = (
        f"A new table '{table_name}' has been added to the Data Warehouse. "
        f"Analyze its structure and ETL context, then generate a semantic description."
    )

    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=user_message)]},
        config={"recursion_limit": 15},
    )

    description = result["messages"][-1].content

    vector_store.upsert(
        table_name=table_name,
        description=description,
        metadata={"source": "ingestion_agent"},
    )

    logger.info("Ingestion complete for table: %s", table_name)

    return {
        "table_name": table_name,
        "description": description,
        "message_count": len(result["messages"]),
    }


if __name__ == "__main__":
    import asyncio
    import sys

    from connectors.dwh import DWHConnector

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    async def test_ingestion() -> None:
        dwh = DWHConnector()
        dwh.init_from_files()
        # Create dm_contract_report for the test
        dwh.execute_script("""
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
        """)

        vector_store = VectorStoreConnector()
        mcp_cmd = [sys.executable, "-m", "mcp_server"]

        mcp_client = MultiServerMCPClient(
            {"dwh-tools": {"command": mcp_cmd[0], "args": mcp_cmd[1:], "transport": "stdio"}}
        )
        result = await run_ingestion("dm_contract_report", mcp_client, vector_store)
        print(f"\n=== Ingestion Result ===")
        print(f"Table: {result['table_name']}")
        print(f"Messages: {result['message_count']}")
        print(f"Description ({len(result['description'])} chars):")
        print(result["description"][:500])

        dwh.close()
        import os
        os.remove(str(dwh._db_path))
        print("\nIngestion Agent OK")

    asyncio.run(test_ingestion())
