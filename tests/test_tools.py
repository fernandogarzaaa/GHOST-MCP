"""Unit tests for the GHOST-MCP tool registry and stdio server."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from ghost_mcp import tools as tools_mod
from ghost_mcp.compress import maybe_compress
from ghost_mcp.tools import all_tools


def test_registry_has_18_well_formed_tools():
    specs = all_tools()
    assert len(specs) == 18
    names = [t.name for t in specs]
    assert len(set(names)) == len(names), "tool names must be unique"
    for t in specs:
        assert t.name.startswith("ghost_")
        assert t.description
        assert t.input_schema.get("type") == "object"
        assert callable(t.handler)


def test_shell_reports_missing_cli(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("ghostchimera")

    monkeypatch.setattr(tools_mod.subprocess, "run", boom)
    out = tools_mod._shell(["doctor"])
    assert out["exit_code"] == 127
    assert "not found" in out["stderr"]


def test_shell_reports_timeout(monkeypatch):
    def slow(*a, **k):
        raise subprocess.TimeoutExpired(cmd="ghostchimera", timeout=300)

    monkeypatch.setattr(tools_mod.subprocess, "run", slow)
    out = tools_mod._shell(["doctor"])
    assert out["exit_code"] == 124


def test_maybe_compress_passthrough():
    payload = {"a": 1}
    assert maybe_compress(payload, enabled=False) is payload
    # Small payloads are returned unchanged even when compression is on.
    assert maybe_compress(payload, enabled=True) is payload


def test_stdio_server_lists_tools():
    proc = subprocess.Popen(
        [sys.executable, "-m", "ghost_mcp"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
    )

    def send(m):
        proc.stdin.write(json.dumps(m) + "\n")
        proc.stdin.flush()

    def recv():
        line = proc.stdout.readline()
        if not line:
            pytest.fail(f"server exited: {proc.stderr.read()}")
        return json.loads(line)

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                         "clientInfo": {"name": "pytest", "version": "0"}}})
        assert recv()["result"]["serverInfo"]["name"] == "ghost-mcp"
        send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        assert len(recv()["result"]["tools"]) == 18
    finally:
        proc.terminate()
        proc.wait(timeout=5)
