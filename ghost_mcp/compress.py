"""Optional runtime compression of tool outputs via chimeralang-mcp.

Tools accept `compress=True` to route oversized outputs through
chimera_log_compress (logs) or chimera_optimize (prose). Falls back to
the raw payload if chimeralang-mcp is not installed or the compressor fails.

`maybe_compress_async` is the real implementation and awaits
chimeralang-mcp's async `call_tool` directly. `maybe_compress` is a sync
wrapper that is safe both with and without a running event loop (the MCP
server runs tool handlers in a worker thread; see ghost_mcp/server.py).
Previously the sync path called `asyncio.run` inside the server's running
loop, which raised, was swallowed, and made `compress=True` a silent no-op.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
from typing import Any, Awaitable, Callable

_THRESHOLD = 800
_LOG_HINTS = ("INFO", "ERROR", "WARN", "DEBUG", "Traceback")

log = logging.getLogger(__name__)

CallTool = Callable[[str, dict[str, Any]], Awaitable[Any]]


def _is_log(text: str) -> bool:
    head = text[:2000]
    return any(h in head for h in _LOG_HINTS)


def _plan(payload: Any, enabled: bool) -> tuple[str, dict[str, Any]] | None:
    """Return (tool, args) when the payload should be compressed, else None."""
    if not enabled:
        return None
    text = payload if isinstance(payload, str) else json.dumps(payload, default=str)
    if len(text) < _THRESHOLD:
        return None
    if _is_log(text):
        return "chimera_log_compress", {"text": text}
    return "chimera_optimize", {"text": text, "level": "high"}


def _default_call_tool() -> CallTool | None:
    try:
        from chimeralang_mcp import server as srv  # type: ignore
    except ImportError:
        return None
    return srv.call_tool


def _extract(result: Any, payload: Any) -> Any:
    for item in getattr(result, "content", None) or []:
        blob = getattr(item, "text", None)
        if blob:
            data = json.loads(blob)
            return data.get("optimised_text") or data.get("compressed") or payload
    return payload


async def maybe_compress_async(
    payload: Any, *, enabled: bool, call_tool: CallTool | None = None
) -> Any:
    """Return payload as-is, or a compressed string if `enabled` and large."""
    plan = _plan(payload, enabled)
    if plan is None:
        return payload
    call_tool = call_tool or _default_call_tool()
    if call_tool is None:
        return payload
    tool, args = plan
    try:
        result = await call_tool(tool, args)
        return _extract(result, payload)
    except Exception:  # compression is best-effort; never fail the tool call
        log.warning("chimeralang-mcp compression failed; returning raw output", exc_info=True)
        return payload


def maybe_compress(payload: Any, *, enabled: bool, call_tool: CallTool | None = None) -> Any:
    """Sync wrapper around `maybe_compress_async`.

    Without a running event loop it uses `asyncio.run`. Inside a running loop
    (where `asyncio.run` would raise) it runs the coroutine on a short-lived
    helper thread with its own loop and waits for the result.
    """
    if _plan(payload, enabled) is None:
        return payload

    def run() -> Any:
        return asyncio.run(maybe_compress_async(payload, enabled=enabled, call_tool=call_tool))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return run()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(run).result()
