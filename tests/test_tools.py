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


def test_threshold_boundary_and_log_hint_window():
    calls: list = []
    fake = _fake_call_tool({"optimised_text": "SHORT"}, calls)
    just_under = "a" * 799
    exactly = "a" * 800
    assert asyncio.run(maybe_compress_async(just_under, enabled=True, call_tool=fake)) is just_under
    assert asyncio.run(maybe_compress_async(exactly, enabled=True, call_tool=fake)) == "SHORT"
    # Log hints are only looked for in the first 2000 characters.
    late_hint = "a" * 2000 + "ERROR"
    near_hint = "a" * 1995 + "ERROR"
    asyncio.run(maybe_compress_async(late_hint, enabled=True, call_tool=fake))
    asyncio.run(maybe_compress_async(near_hint, enabled=True, call_tool=fake))
    assert [c[0] for c in calls[1:]] == ["chimera_optimize", "chimera_log_compress"]


def test_missing_chimeralang_or_empty_content_returns_payload(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def no_chimeralang(name, *a, **k):
        if name.startswith("chimeralang_mcp"):
            raise ImportError(name)
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_chimeralang)
    assert compress_mod._default_call_tool() is None
    assert asyncio.run(maybe_compress_async(_BIG, enabled=True)) is _BIG
    monkeypatch.setattr(builtins, "__import__", real_import)

    async def no_content(name, arguments):
        return _pytypes.SimpleNamespace(content=[])

    assert asyncio.run(maybe_compress_async(_BIG, enabled=True, call_tool=no_content)) is _BIG


# --- error reporting + args coercion (Oct 2026) -------------------------------


def _call(name, arguments):
    from ghost_mcp import server as server_mod

    params = _pytypes.SimpleNamespace(name=name, arguments=arguments)
    return asyncio.run(server_mod._call_tool(None, params))


def test_handler_exception_is_flagged_as_error(monkeypatch):
    def boom(args):
        raise RuntimeError("ghost exploded")

    from ghost_mcp import server as server_mod

    monkeypatch.setattr(server_mod._TOOLS["ghost_doctor"], "handler", boom)
    res = _call("ghost_doctor", {})
    assert res.is_error is True
    assert json.loads(res.content[0].text) == {"error": "RuntimeError: ghost exploded"}


def test_missing_required_argument_is_a_clear_error(monkeypatch):
    # ghost_search requires "query"; the SDK search must never be reached.
    client = _pytypes.SimpleNamespace(search=lambda *a, **k: pytest.fail("search called"))
    monkeypatch.setattr(tools_mod, "_get_client", lambda: client)
    res = _call("ghost_search", {})
    assert res.is_error is True
    assert json.loads(res.content[0].text) == {"error": "missing required argument: query"}


def test_success_is_not_flagged_as_error(monkeypatch):
    monkeypatch.setattr(tools_mod, "_shell", lambda a: {"exit_code": 0, "stdout": "ok", "stderr": ""})
    res = _call("ghost_doctor", {})
    assert res.is_error is False
    assert json.loads(res.content[0].text)["stdout"] == "ok"


def test_string_args_are_one_argument_not_characters(monkeypatch):
    seen = []
    monkeypatch.setattr(tools_mod, "_shell", lambda a: seen.append(a) or {"exit_code": 0})
    tools_mod._ghost_models({"args": "list"})
    tools_mod._ghost_trust({"action": "runs", "args": "--json"})
    tools_mod._ghost_eval({"args": ["compare", 3]})
    tools_mod._ghost_doctor({"args": None})
    assert seen == [
        ["model", "list"],
        ["trust", "runs", "--json"],
        ["trust", "eval", "status", "compare", "3"],
        ["doctor"],
    ]


def test_non_list_args_rejected_with_error_result():
    with pytest.raises(ValueError):
        tools_mod._argv({"args": {"a": 1}})
    res = _call("ghost_doctor", {"args": {"a": 1}})
    assert res.is_error is True
    assert "must be a list" in res.content[0].text


def test_shell_strips_ansi_colour_codes(monkeypatch):
    captured = {}

    def fake_run(cmd, **kw):
        captured.update(kw)
        return _pytypes.SimpleNamespace(
            returncode=0,
            stdout="\x1b[1m\x1b[96m  == Doctor ==\x1b[0m\n  \x1b[92m[OK] Python\x1b[0m\n",
            stderr="\x1b]8;;http://x\x07link\x1b]8;;\x07 \x1b[93mwarn\x1b[0m",
        )

    monkeypatch.setattr(tools_mod.subprocess, "run", fake_run)
    out = tools_mod._shell(["doctor"])
    assert out == {"exit_code": 0, "stdout": "  == Doctor ==\n  [OK] Python\n", "stderr": "link warn"}
    assert captured["env"]["NO_COLOR"] == "1"
    assert tools_mod._strip_ansi(None) == ""
