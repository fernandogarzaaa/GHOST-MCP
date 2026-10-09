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
from mcp.server.context import ServerRequestContext
from mcp.server.stdio import stdio_server

from ghost_mcp.tools import all_tools

_TOOLS = {t.name: t for t in all_tools()}


async def _list_tools(
    ctx: ServerRequestContext, params: types.PaginatedRequestParams | None
) -> types.ListToolsResult:
    return types.ListToolsResult(
        tools=[
            types.Tool(name=t.name, description=t.description, inputSchema=t.input_schema)
            for t in _TOOLS.values()
        ]
    )


async def _call_tool(
    ctx: ServerRequestContext, params: types.CallToolRequestParams
) -> types.CallToolResult:
    spec = _TOOLS.get(params.name)
    if spec is None:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text", text=json.dumps({"error": f"unknown tool: {params.name}"})
                )
            ],
            is_error=True,
        )
    try:
        result = spec.handler(params.arguments or {})
    except Exception as exc:
        result = {"error": f"{type(exc).__name__}: {exc}"}
    text = result if isinstance(result, str) else json.dumps(result, default=str)
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)])


server: Server = Server(
    "ghost-mcp",
    on_list_tools=_list_tools,
    on_call_tool=_call_tool,
)


async def _run() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> int:
    asyncio.run(_run())
    return 0
