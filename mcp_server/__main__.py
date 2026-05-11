"""MCP server entry point for `python -m mcp_server`."""

import asyncio

from mcp_server.server import run_server

if __name__ == "__main__":
    asyncio.run(run_server())
