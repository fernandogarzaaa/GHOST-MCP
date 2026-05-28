"""GHOST-MCP tool registry.

Each tool maps to either:
- a method on ghostchimera.sdk.GhostClient (preferred), or
- a thin subprocess shell-out to `ghostchimera <subcommand>` when no SDK
  method exists.

Tools accept an optional `compress` bool that pipes the result through
chimeralang-mcp's compressor before return.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Callable

from ghost_mcp.compress import maybe_compress


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]


_client = None


def _get_client():
    global _client
    if _client is None:
        from ghostchimera.sdk import GhostClient
        _client = GhostClient()
    return _client


def _result_to_dict(result: Any) -> Any:
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items() if not k.startswith("_")}
    return result


def _shell(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        ["ghostchimera", *args],
        capture_output=True, text=True, timeout=300,
    )
    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


# --- SDK-backed tools ---------------------------------------------------

def _ghost_run(args: dict[str, Any]) -> Any:
    out = _get_client().run(args["objective"])
    return maybe_compress(_result_to_dict(out), enabled=bool(args.get("compress")))


def _ghost_teach(args: dict[str, Any]) -> Any:
    out = _get_client().teach(args["question"], args["answer"])
    return maybe_compress(_result_to_dict(out), enabled=bool(args.get("compress")))


def _ghost_ingest(args: dict[str, Any]) -> Any:
    c = _get_client()
    kind = args.get("kind", "file")
    target = args["target"]
    if kind == "file":
        out = c.ingest_file(target)
    elif kind == "directory":
        out = c.ingest_directory(target, max_files=int(args.get("max_files", 500)))
    elif kind == "email_file":
        out = c.ingest_email_file(target)
    elif kind == "raw_email":
        out = c.ingest_raw_email(target)
    elif kind == "document":
        out = c.ingest_document(args.get("name", "doc"), target)
    else:
        raise ValueError(f"Unknown kind: {kind}")
    return maybe_compress(_result_to_dict(out), enabled=bool(args.get("compress")))


def _ghost_search(args: dict[str, Any]) -> Any:
    hits = _get_client().search(args["query"], limit=int(args.get("limit", 5)))
    return maybe_compress(hits, enabled=bool(args.get("compress")))


def _ghost_memory_status(args: dict[str, Any]) -> Any:
    c = _get_client()
    return {
        "count": c.memory_count(),
        "training": c.training_status(),
    }


def _ghost_preview_context(args: dict[str, Any]) -> Any:
    out = _get_client().preview_context(args["objective"], limit=int(args.get("limit", 5)))
    return maybe_compress(out, enabled=bool(args.get("compress")))


def _ghost_minimind(args: dict[str, Any]) -> Any:
    c = _get_client()
    action = args.get("action", "status")
    if action == "status":
        return c.personal_minimind_status()
    if action == "enable":
        return c.enable_personal_minimind(**args.get("options", {}))
    if action == "revoke":
        return c.revoke_personal_minimind()
    if action == "bootstrap":
        return c.bootstrap_personal_minimind(**args.get("options", {}))
    if action == "handoff":
        return c.minimind_handoff(args["objective"], limit=int(args.get("limit", 8)))
    raise ValueError(f"Unknown minimind action: {action}")


# --- CLI-backed tools (no SDK method) -----------------------------------

def _ghost_trust(args: dict[str, Any]) -> Any:
    sub = args.get("action", "status")
    extra = args.get("args", [])
    out = _shell(["trust", sub, *extra])
    return maybe_compress(out, enabled=bool(args.get("compress")))


def _ghost_review_pr(args: dict[str, Any]) -> Any:
    extra = args.get("args", [])
    out = _shell(["review-pr", *extra])
    return maybe_compress(out, enabled=bool(args.get("compress")))


def _ghost_gaps(args: dict[str, Any]) -> Any:
    out = _shell(["production-gaps", *args.get("args", [])])
    return maybe_compress(out, enabled=bool(args.get("compress")))


def _ghost_doctor(args: dict[str, Any]) -> Any:
    return _shell(["doctor", *args.get("args", [])])


def _ghost_models(args: dict[str, Any]) -> Any:
    return _shell(["model", *args.get("args", [])])


def _ghost_autonomy(args: dict[str, Any]) -> Any:
    return _shell(["autonomy", *args.get("args", [])])


def _ghost_console(args: dict[str, Any]) -> Any:
    return _shell(["console", *args.get("args", [])])


def _ghost_capabilities(args: dict[str, Any]) -> Any:
    return _shell(["capabilities", *args.get("args", [])])


def _ghost_path(args: dict[str, Any]) -> Any:
    return _shell(["path", *args.get("args", [])])


def _ghost_orders(args: dict[str, Any]) -> Any:
    return _shell(["standing-orders", *args.get("args", [])])


def _ghost_eval(args: dict[str, Any]) -> Any:
    sub = args.get("action", "status")
    return _shell(["trust", "eval", sub, *args.get("args", [])])


# --- Registry -----------------------------------------------------------

_COMPRESS_FIELD = {
    "compress": {"type": "boolean", "default": False,
                 "description": "Route oversized output through chimeralang-mcp compressor."}
}


def all_tools() -> list[ToolSpec]:
    return [
        ToolSpec(
            "ghost_run",
            "Run a natural-language objective through Chimera Pilot. Returns execution result with telemetry.",
            {"type": "object",
             "properties": {"objective": {"type": "string"}, **_COMPRESS_FIELD},
             "required": ["objective"]},
            _ghost_run,
        ),
        ToolSpec(
            "ghost_teach",
            "Add a Q&A pair to Ghost's personal memory for future RAG injection.",
            {"type": "object",
             "properties": {"question": {"type": "string"}, "answer": {"type": "string"}, **_COMPRESS_FIELD},
             "required": ["question", "answer"]},
            _ghost_teach,
        ),
        ToolSpec(
            "ghost_ingest",
            "Ingest a file/directory/email/document into Ghost's local memory.",
            {"type": "object",
             "properties": {
                 "kind": {"type": "string", "enum": ["file", "directory", "email_file", "raw_email", "document"]},
                 "target": {"type": "string"},
                 "name": {"type": "string"},
                 "max_files": {"type": "integer"},
                 **_COMPRESS_FIELD},
             "required": ["target"]},
            _ghost_ingest,
        ),
        ToolSpec(
            "ghost_search",
            "Semantic search over Ghost's personal memory.",
            {"type": "object",
             "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}, **_COMPRESS_FIELD},
             "required": ["query"]},
            _ghost_search,
        ),
        ToolSpec(
            "ghost_memory_status",
            "Report Ghost memory size and training status.",
            {"type": "object", "properties": {}},
            _ghost_memory_status,
        ),
        ToolSpec(
            "ghost_preview_context",
            "Preview the RAG snippets Ghost would inject for an objective.",
            {"type": "object",
             "properties": {"objective": {"type": "string"}, "limit": {"type": "integer", "default": 5}, **_COMPRESS_FIELD},
             "required": ["objective"]},
            _ghost_preview_context,
        ),
        ToolSpec(
            "ghost_minimind",
            "Manage Personal MiniMind. action: status|enable|revoke|bootstrap|handoff.",
            {"type": "object",
             "properties": {
                 "action": {"type": "string", "enum": ["status", "enable", "revoke", "bootstrap", "handoff"]},
                 "objective": {"type": "string"},
                 "options": {"type": "object"},
                 "limit": {"type": "integer"}}},
            _ghost_minimind,
        ),
        ToolSpec(
            "ghost_trust",
            "Trust Runtime: durable runs, traces, evals, approvals. action: status|runs|trace|eval|eval-cases.",
            {"type": "object",
             "properties": {
                 "action": {"type": "string"},
                 "args": {"type": "array", "items": {"type": "string"}},
                 **_COMPRESS_FIELD}},
            _ghost_trust,
        ),
        ToolSpec(
            "ghost_review_pr",
            "Deterministic PR/diff review: secrets, destructive cmds, missing tests, beta drift.",
            {"type": "object",
             "properties": {"args": {"type": "array", "items": {"type": "string"}}, **_COMPRESS_FIELD}},
            _ghost_review_pr,
        ),
        ToolSpec(
            "ghost_gaps",
            "Scan codebase for scaffold/placeholder/TODO/demo markers before release.",
            {"type": "object",
             "properties": {"args": {"type": "array", "items": {"type": "string"}}, **_COMPRESS_FIELD}},
            _ghost_gaps,
        ),
        ToolSpec(
            "ghost_doctor",
            "Run Ghost health checks and report status.",
            {"type": "object", "properties": {"args": {"type": "array", "items": {"type": "string"}}}},
            _ghost_doctor,
        ),
        ToolSpec(
            "ghost_models",
            "List or switch Ghost's current model provider (27 providers supported).",
            {"type": "object", "properties": {"args": {"type": "array", "items": {"type": "string"}}}},
            _ghost_models,
        ),
        ToolSpec(
            "ghost_autonomy",
            "Show, set, or run autonomy profile controls.",
            {"type": "object", "properties": {"args": {"type": "array", "items": {"type": "string"}}}},
            _ghost_autonomy,
        ),
        ToolSpec(
            "ghost_console",
            "Open or manage the Ghost Console browser UI.",
            {"type": "object", "properties": {"args": {"type": "array", "items": {"type": "string"}}}},
            _ghost_console,
        ),
        ToolSpec(
            "ghost_capabilities",
            "List/inspect registered capabilities (skills, tools, backends).",
            {"type": "object", "properties": {"args": {"type": "array", "items": {"type": "string"}}}},
            _ghost_capabilities,
        ),
        ToolSpec(
            "ghost_path",
            "Show/list/persist the active multi-purpose Ghost path.",
            {"type": "object", "properties": {"args": {"type": "array", "items": {"type": "string"}}}},
            _ghost_path,
        ),
        ToolSpec(
            "ghost_orders",
            "Manage Standing Orders (scoped reusable autonomy programs).",
            {"type": "object", "properties": {"args": {"type": "array", "items": {"type": "string"}}}},
            _ghost_orders,
        ),
        ToolSpec(
            "ghost_eval",
            "Create/compare local trust eval baselines and harness cases.",
            {"type": "object",
             "properties": {"action": {"type": "string"}, "args": {"type": "array", "items": {"type": "string"}}}},
            _ghost_eval,
        ),
    ]
