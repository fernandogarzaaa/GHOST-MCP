---
name: ghost
description: Use Ghost-Chimera capabilities — local-first agent orchestration, Trust Runtime, MiniMind personal memory, and PR/production-gap automation. Triggers when the user asks about Ghost, GHOST-Chimera, Chimera Pilot, MiniMind, Trust Runtime, Standing Orders, or wants to run an objective against their local agent.
---

# GHOST Skill — Routing Matrix

This plugin exposes the GHOST-Chimera agent runtime through MCP. Ghost is a local-first agent orchestrator with Chimera Pilot scheduling, 27 model providers, durable Trust Runtime, MiniMind personal memory, and a Ghost Console browser UI.

## When to invoke which tool

| Situation | Tool |
|-----------|------|
| User states an objective in natural language ("plan a refactor of X", "summarise these docs") | `ghost_run` |
| User wants Ghost to remember a fact for future runs | `ghost_teach` (Q&A pair) |
| User points at files/dirs/emails to feed personal memory | `ghost_ingest` (kind=file/directory/email_file/raw_email/document) |
| User asks "what do I know about X" in Ghost memory | `ghost_search` |
| Inspect memory size, training readiness | `ghost_memory_status` |
| Preview what RAG snippets Ghost would inject for an objective | `ghost_preview_context` |
| Personal MiniMind lifecycle (consent-gated local LLM seed) | `ghost_minimind` action=status/enable/revoke/bootstrap/handoff |
| Durable runs, approvals, OTel traces, eval baselines | `ghost_trust` action=status/runs/trace/eval/eval-cases |
| Pre-merge PR review (secrets, destructive cmds, missing tests) | `ghost_review_pr` |
| Pre-release scan for scaffold/TODO/demo markers | `ghost_gaps` |
| Health check of the local Ghost install | `ghost_doctor` |
| List/switch model provider | `ghost_models` |
| View/set autonomy profile | `ghost_autonomy` |
| Launch browser console (Ghost Console) | `ghost_console` |
| List skills/tools/backends | `ghost_capabilities` |
| Active path management | `ghost_path` |
| Standing Orders (reusable autonomy programs) | `ghost_orders` |
| Run harness/eval suites | `ghost_eval` |

## Calling conventions

- All tools accept `compress=true` to route oversized output through chimeralang-mcp before return. Default off — flip when context is tight.
- Multi-action tools (`ghost_minimind`, `ghost_trust`, `ghost_eval`) take an `action` arg covering CLI subcommands.
- CLI-shell tools accept `args` as an array of additional CLI flags.

## Quick examples

```
# Run an objective
ghost_run({"objective": "Summarise the changes in the last 5 commits and flag risky ones."})

# Teach a fact
ghost_teach({"question": "What's our database?", "answer": "PostgreSQL 16 on RDS."})

# Ingest a whole directory of docs
ghost_ingest({"kind": "directory", "target": "/path/to/notes", "max_files": 200})

# Preview RAG injection for an objective
ghost_preview_context({"objective": "Draft a release blog post.", "limit": 8})

# Scan a working tree for production gaps
ghost_gaps({"args": ["--path", "."]})

# Inspect durable runs
ghost_trust({"action": "runs", "args": ["list", "--limit", "10"]})
```

## Safety model

Ghost defaults to conservative: Python, shell, network, and desktop execution are all **off** by default. Production mode adds extra guardrails. The plugin honours those defaults — if a tool returns a "capability not admitted" error, the user must explicitly admit the capability via `ghost_trust action=capability-admission` or the Ghost Console.

## When NOT to use Ghost tools

- Single-turn questions with no objective → answer directly.
- File edits the user can do via Edit/Write → use those tools directly.
- Pure search/grep of the current repo → use Bash/grep, not `ghost_search` (which searches Ghost memory, not the repo).
