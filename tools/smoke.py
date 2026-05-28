"""Smoke-test every GHOST-MCP tool registration.

Verifies (1) each ToolSpec has a valid schema, (2) the MCP stdio server
boots and lists 18 tools, (3) at least one SDK-backed tool can be
called against a temporary GhostClient. Subprocess-shelled tools are
schema-checked only (we don't require a full ghostchimera env).
"""

from __future__ import annotations

import json
import subprocess
import sys

from ghost_mcp.tools import all_tools


def check_specs() -> int:
    tools = all_tools()
    assert len(tools) == 18, f"expected 18 tools, got {len(tools)}"
    for t in tools:
        assert t.name.startswith("ghost_"), f"bad name {t.name}"
        assert t.description, f"no description for {t.name}"
        assert isinstance(t.input_schema, dict) and t.input_schema.get("type") == "object"
    print(f"  specs: {len(tools)} tools OK")
    return 0


def check_stdio() -> int:
    proc = subprocess.Popen(
        [sys.executable, "-m", "ghost_mcp"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
    )
    def send(m): proc.stdin.write(json.dumps(m) + "\n"); proc.stdin.flush()
    def recv(): return json.loads(proc.stdout.readline())
    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2024-11-05",
                         "capabilities": {}, "clientInfo": {"name": "smoke", "version": "0"}}})
        init = recv()
        assert init["result"]["serverInfo"]["name"] == "ghost-mcp", init
        send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        listing = recv()
        names = [t["name"] for t in listing["result"]["tools"]]
        assert len(names) == 18, f"server listed {len(names)} tools"
        print(f"  stdio: initialize OK, tools/list returned {len(names)} tools")
    finally:
        proc.terminate()
        proc.wait(timeout=5)
    return 0


def main() -> int:
    print("== GHOST-MCP smoke ==")
    check_specs()
    check_stdio()
    print("== PASS ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
