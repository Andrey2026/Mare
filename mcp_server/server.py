"""MCP server entry point — stdio transport."""

import json
import logging
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from connectors.dwh import DWHConnector
from mcp_server.dwh_tools import analyze_query_plan, get_table_schema
from mcp_server.etl_tools import find_etl_process_by_table, get_process_execution_status
from mcp_server.log_tools import fetch_recent_logs, get_table_increment_stats

logger = logging.getLogger(__name__)

app = Server("mare-dwh-tools")
dwh = DWHConnector()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Return available tools."""
    return [
        Tool(
            name="get_table_schema",
            description=(
                "Returns DDL definition (CREATE TABLE) of a table. "
                "Used for analyzing table structure."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Table name, e.g. 'dim_contract'",
                    }
                },
                "required": ["table_name"],
            },
        ),
        Tool(
            name="analyze_query_plan",
            description=(
                "Validates SQL syntax (SELECT only) and returns execution plan. "
                "Used for verification of generated SQL and diagnosing suboptimal queries."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SELECT SQL query to analyze",
                    }
                },
                "required": ["sql"],
            },
        ),
        Tool(
            name="find_etl_process_by_table",
            description=(
                "Finds ETL processes that load data into the specified target table. "
                "Returns process name, schedule, and source tables."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Target table name, e.g. 'dm_contract_report'",
                    }
                },
                "required": ["table_name"],
            },
        ),
        Tool(
            name="get_process_execution_status",
            description=(
                "Returns history of last 5 executions of an ETL process: "
                "start/end time, status, rows affected, duration."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "process_name": {
                        "type": "string",
                        "description": "ETL process name, e.g. 'etl_refresh_dm_contract_report'",
                    }
                },
                "required": ["process_name"],
            },
        ),
        Tool(
            name="fetch_recent_logs",
            description=(
                "Extracts recent text log entries of an ETL process. "
                "Contains level (INFO/WARNING/ERROR) and messages."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "process_name": {
                        "type": "string",
                        "description": "ETL process name",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of log entries (default 50)",
                        "default": 50,
                    },
                },
                "required": ["process_name"],
            },
        ),
        Tool(
            name="get_table_increment_stats",
            description=(
                "Estimates data volume in the last table increment and compares to average. "
                "Reveals anomalous data growth that may cause ETL slowdowns."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Target table name of ETL process",
                    }
                },
                "required": ["table_name"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Dispatch tool call to implementation."""
    dwh.connect()

    if name == "get_table_schema":
        result = get_table_schema(dwh, arguments["table_name"])
    elif name == "analyze_query_plan":
        result = analyze_query_plan(dwh, arguments["sql"])
    elif name == "find_etl_process_by_table":
        result = find_etl_process_by_table(dwh, arguments["table_name"])
    elif name == "get_process_execution_status":
        result = get_process_execution_status(dwh, arguments["process_name"])
    elif name == "fetch_recent_logs":
        limit = arguments.get("limit", 50)
        result = fetch_recent_logs(dwh, arguments["process_name"], limit)
    elif name == "get_table_increment_stats":
        result = get_table_increment_stats(dwh, arguments["table_name"])
    else:
        result = f"Unknown tool: {name}"

    text = json.dumps(result, ensure_ascii=False, default=str)
    return [TextContent(type="text", text=text)]


async def run_server() -> None:
    """Run the MCP server via stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_server())
