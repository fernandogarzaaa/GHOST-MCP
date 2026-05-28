"""Optional runtime compression of tool outputs via chimeralang-mcp.

Tools accept `compress=True` to route oversized outputs through
chimera_log_compress (logs) or chimera_optimize (prose). Falls back to
the raw payload if chimeralang-mcp is not installed.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

_THRESHOLD = 800
_LOG_HINTS = ("INFO", "ERROR", "WARN", "DEBUG", "Traceback")


def _is_log(text: str) -> bool:
    head = text[:2000]
    return any(h in head for h in _LOG_HINTS)


def maybe_compress(payload: Any, *, enabled: bool) -> Any:
    """Return payload as-is, or a compressed string if `enabled` and large."""
    if not enabled:
        return payload
    text = payload if isinstance(payload, str) else json.dumps(payload, default=str)
    if len(text) < _THRESHOLD:
        return payload
    try:
        from chimeralang_mcp import server as srv  # type: ignore
    except ImportError:
        return payload
    tool = "chimera_log_compress" if _is_log(text) else "chimera_optimize"
    args = {"text": text} if tool == "chimera_log_compress" else {"text": text, "level": "high"}
    try:
        result = asyncio.run(srv.call_tool(tool, args))
        for item in result.content:
            blob = getattr(item, "text", None)
            if blob:
                data = json.loads(blob)
                return data.get("optimised_text") or data.get("compressed") or payload
    except Exception:
        return payload
    return payload
