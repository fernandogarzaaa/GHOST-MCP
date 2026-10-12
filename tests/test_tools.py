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


# --- compression path (regression: compress=True was a silent no-op) ----------

import asyncio
import types as _pytypes

from ghost_mcp import compress as compress_mod
from ghost_mcp.compress import maybe_compress_async

_BIG = {"text": "The quick brown fox jumps over the lazy dog. " * 100}
_BIG_LOG = "INFO starting worker\n" + "ERROR something failed in step 3\n" * 60


def _fake_call_tool(reply: dict, calls: list):
    async def call_tool(name, arguments):
        await asyncio.sleep(0)  # a real coroutine, like chimeralang-mcp's
        calls.append((name, arguments))
        item = _pytypes.SimpleNamespace(text=json.dumps(reply))
        return _pytypes.SimpleNamespace(content=[item])

    return call_tool


def test_maybe_compress_works_inside_a_running_event_loop():
    calls: list = []
    fake = _fake_call_tool({"optimised_text": "SHORT"}, calls)

    async def inside_loop():
        # The MCP server calls tools from inside its running loop. Before the
        # fix, asyncio.run raised here and the raw payload came back silently.
        return compress_mod.maybe_compress(_BIG, enabled=True, call_tool=fake)

    assert asyncio.run(inside_loop()) == "SHORT"
    assert calls[0][0] == "chimera_optimize"
    assert calls[0][1]["level"] == "high"
    assert json.loads(calls[0][1]["text"]) == _BIG


def test_maybe_compress_without_running_loop():
    calls: list = []
    fake = _fake_call_tool({"optimised_text": "SHORT"}, calls)
    assert compress_mod.maybe_compress(_BIG, enabled=True, call_tool=fake) == "SHORT"
    assert len(calls) == 1


def test_async_compress_routes_logs_and_reads_compressed_key():
    calls: list = []
    fake = _fake_call_tool({"compressed": "LOGS"}, calls)
    out = asyncio.run(maybe_compress_async(_BIG_LOG, enabled=True, call_tool=fake))
    assert out == "LOGS"
    assert calls == [("chimera_log_compress", {"text": _BIG_LOG})]


def test_async_compress_falls_back_on_error_or_empty_reply():
    async def broken(name, arguments):
        raise RuntimeError("compressor down")

    assert asyncio.run(maybe_compress_async(_BIG, enabled=True, call_tool=broken)) is _BIG
    calls: list = []
    empty = _fake_call_tool({}, calls)
    assert asyncio.run(maybe_compress_async(_BIG, enabled=True, call_tool=empty)) is _BIG


def test_async_compress_skips_small_or_disabled():
    calls: list = []
    fake = _fake_call_tool({"optimised_text": "SHORT"}, calls)
    assert asyncio.run(maybe_compress_async(_BIG, enabled=False, call_tool=fake)) is _BIG
    small = {"a": "x" * 10}
    assert asyncio.run(maybe_compress_async(small, enabled=True, call_tool=fake)) is small
    assert calls == []


def test_server_call_tool_compresses_through_running_loop(monkeypatch):
    """End to end through ghost_mcp.server._call_tool with a fake compressor."""
    from ghost_mcp import server as server_mod

    calls: list = []
    fake = _fake_call_tool({"optimised_text": "SHORT"}, calls)
    monkeypatch.setattr(compress_mod, "_default_call_tool", lambda: fake)
    monkeypatch.setattr(tools_mod, "_shell", lambda args: {"exit_code": 0, "stdout": "y" * 2000, "stderr": ""})
    name = next(n for n, t in server_mod._TOOLS.items() if t.handler is tools_mod._ghost_gaps)
    params = _pytypes.SimpleNamespace(name=name, arguments={"compress": True})
    res = asyncio.run(server_mod._call_tool(None, params))
    assert res.content[0].text == "SHORT"
    assert len(calls) == 1


def test_real_chimeralang_compression_path():
    """Exercise the real chimeralang-mcp compressor when it is installed."""
    pytest.importorskip("chimeralang_mcp")

    async def inside_loop():
        return compress_mod.maybe_compress(_BIG, enabled=True)

    out = asyncio.run(inside_loop())
    assert isinstance(out, str), "compression must actually run inside a loop"
    assert len(out) < len(json.dumps(_BIG))
