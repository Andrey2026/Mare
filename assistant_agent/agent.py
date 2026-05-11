"""Assistant Agent — LangGraph ReAct graph with MCP tools and RAG."""

import logging
import time
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from connectors.llm import get_llm
from connectors.vector_store import VectorStoreConnector
from assistant_agent.prompts import ASSISTANT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _make_search_tool(vector_store: VectorStoreConnector):
    """Create a search tool bound to the given vector store."""

    @tool
    def search_vector_store(query: str) -> str:
        """Search the semantic layer for DWH tables matching the query.

        Use this to find tables by business meaning, purpose, or context.
        Returns table names and their semantic descriptions.

        Args:
            query: Natural language description of what you're looking for.
        """
        results = vector_store.search(query, top_k=3)
        if not results:
            return "No matching tables found in the semantic layer."

        parts = []
        for r in results:
            parts.append(
                f"Table: {r['table_name']}\n"
                f"Description: {r['description']}\n"
                f"Similarity score: {r['score']:.4f}"
            )
        return "\n---\n".join(parts)

    return search_vector_store


async def run_assistant(
    question: str,
    mcp_client: MultiServerMCPClient,
    vector_store: VectorStoreConnector,
) -> dict[str, Any]:
    """Run Assistant Agent for a user question.

    Args:
        question: User's natural language question.
        mcp_client: Connected MCP client with DWH tools.
        vector_store: Vector store connector for semantic search.

    Returns:
        Dict with question, answer, retrieved_contexts, duration_seconds, messages.
    """
    llm = get_llm()

    mcp_tools = await mcp_client.get_tools()
    search_tool = _make_search_tool(vector_store)
    all_tools = mcp_tools + [search_tool]

    agent = create_react_agent(
        llm,
        all_tools,
        prompt=ASSISTANT_SYSTEM_PROMPT,
    )

    start_time = time.time()
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=question)]},
        config={"recursion_limit": 25},
    )
    duration = time.time() - start_time

    answer = result["messages"][-1].content

    retrieved_contexts = []
    tool_calls_log = []
    for msg in result["messages"]:
        # Log tool calls (AI deciding to call a tool)
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_log.append({
                    "tool": tc["name"],
                    "args": tc["args"],
                })
                logger.info("Tool call: %s(%s)", tc["name"], tc["args"])
        # Collect tool results as retrieved contexts
        if hasattr(msg, "name") and msg.name:
            content = msg.content
            if isinstance(content, list):
                content = "\n".join(
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in content
                )
            retrieved_contexts.append(str(content))

    logger.info("Assistant answered in %.1fs (%d tool calls)", duration, len(tool_calls_log))

    return {
        "question": question,
        "answer": answer,
        "retrieved_contexts": retrieved_contexts,
        "tool_calls": tool_calls_log,
        "duration_seconds": round(duration, 2),
        "message_count": len(result["messages"]),
    }


if __name__ == "__main__":
    import asyncio
    import sys

    from connectors.dwh import DWHConnector

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    PRECOMPUTED = {
        "dim_contract": (
            "Dimension table for contracts. Contains contract master data: client name, "
            "contract status (active/terminated), assigned manager, start and end dates, "
            "contract type. Business terms: agreement, deal, contract termination."
        ),
        "fact_revenue": (
            "Fact table containing revenue records. Each row is a revenue entry tied to "
            "a contract and time period. Includes amount and revenue type (monthly/final). "
            "Business terms: revenue, income, billing amount."
        ),
        "dim_manager": (
            "Dimension table for managers. Contains manager name and department. "
            "Business terms: account manager, sales representative."
        ),
        "dim_date": (
            "Calendar dimension table. Contains date, year, month, quarter. "
            "Used for time-based aggregation."
        ),
        "dm_contract_report": (
            "Data mart table for contract reporting. Aggregates revenue, events, and "
            "contract details by manager and month. Business terms: contract report, "
            "reporting mart, contract dashboard."
        ),
    }

    async def test_assistant() -> None:
        dwh = DWHConnector()
        dwh.init_from_files()
        dwh.execute_script("""
            CREATE TABLE IF NOT EXISTS dm_contract_report (
                report_id INTEGER PRIMARY KEY, contract_id INTEGER,
                client_name VARCHAR(100), manager_name VARCHAR(100),
                contract_status VARCHAR(20), total_revenue DECIMAL(15,2),
                event_count INTEGER, last_event_date DATE,
                report_month INTEGER, report_year INTEGER
            );
        """)

        vector_store = VectorStoreConnector()
        for name, desc in PRECOMPUTED.items():
            vector_store.upsert(name, desc, {})

        mcp_cmd = [sys.executable, "-m", "mcp_server"]
        mcp_client = MultiServerMCPClient(
            {"dwh-tools": {"command": mcp_cmd[0], "args": mcp_cmd[1:], "transport": "stdio"}}
        )

        question = "Write a query returning revenue from terminated contracts for 2025, by month and responsible managers"
        print(f"\nQuestion: {question}\n")

        result = await run_assistant(question, mcp_client, vector_store)
        print(f"=== Assistant Result ===")
        print(f"Duration: {result['duration_seconds']}s")
        print(f"Messages: {result['message_count']}")
        print(f"Retrieved contexts: {len(result['retrieved_contexts'])}")
        print(f"\nAnswer:\n{result['answer'][:800]}")

        dwh.close()
        import os
        os.remove(str(dwh._db_path))
        print("\nAssistant Agent OK")

    asyncio.run(test_assistant())
