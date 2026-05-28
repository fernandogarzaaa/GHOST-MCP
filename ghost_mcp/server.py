"""GHOST-MCP stdio server.

Real Model Context Protocol JSON-RPC server (initialize, tools/list,
tools/call) using the `mcp` SDK. Bridges into ghostchimera via
ghost_mcp.tools.
"""

from __future__ import annotations

import asyncio
import json

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from ghost_mcp.tools import all_tools

server: Server = Server("ghost-mcp")
_TOOLS = {t.name: t for t in all_tools()}


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name=t.name, description=t.description, inputSchema=t.input_schema)
        for t in _TOOLS.values()
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    spec = _TOOLS.get(name)
    if spec is None:
        return [types.TextContent(type="text", text=json.dumps({"error": f"unknown tool: {name}"}))]
    try:
        result = spec.handler(arguments or {})
    except Exception as exc:
        result = {"error": f"{type(exc).__name__}: {exc}"}
    text = result if isinstance(result, str) else json.dumps(result, default=str)
    return [types.TextContent(type="text", text=text)]


async def _run() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> int:
    asyncio.run(_run())
    return 0
