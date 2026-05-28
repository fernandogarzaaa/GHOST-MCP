# GHOST-MCP

**Ghost Chimera as a Claude plugin.** Install once, get GHOST's local-first agent orchestration, Trust Runtime, MiniMind personal memory, and PR/production automation as MCP tools and slash commands inside any Claude Code session.

## Install

```bash
# In Claude Code
/plugin install fernandogarzaaa/GHOST-MCP

# Or pip install for any MCP client
pip install ghost-mcp
```

The plugin manifest at `.claude-plugin/plugin.json` registers:
- **18 MCP tools** bridging into `ghostchimera.sdk.GhostClient` and the `ghostchimera` CLI
- **9 slash commands** for the operator surface (`/ghost-run`, `/ghost-teach`, `/ghost-trust`, …)
- **1 skill** (`skills/ghost`) — compressed routing matrix, auto-loaded
- **1 SessionStart hook** announcing the capability surface

## Tools

| Tool | Bridges to |
|------|-----------|
| `ghost_run` | `GhostClient.run(objective)` — Chimera Pilot execution |
| `ghost_teach` | `GhostClient.teach(q, a)` — Q&A into memory |
| `ghost_ingest` | `ingest_file/_directory/_email_file/_raw_email/_document` |
| `ghost_search` | `GhostClient.search` — semantic recall |
| `ghost_memory_status` | `memory_count` + `training_status` |
| `ghost_preview_context` | `preview_context` — RAG injection preview |
| `ghost_minimind` | MiniMind lifecycle (status/enable/revoke/bootstrap/handoff) |
| `ghost_trust` | `ghostchimera trust …` — runs/traces/evals/approvals |
| `ghost_review_pr` | `ghostchimera review-pr` |
| `ghost_gaps` | `ghostchimera production-gaps` |
| `ghost_doctor` | `ghostchimera doctor` |
| `ghost_models` | `ghostchimera model` — 27 provider catalogue |
| `ghost_autonomy` | `ghostchimera autonomy` |
| `ghost_console` | `ghostchimera console` — browser UI |
| `ghost_capabilities` | `ghostchimera capabilities` |
| `ghost_path` | `ghostchimera path` |
| `ghost_orders` | `ghostchimera standing-orders` |
| `ghost_eval` | `ghostchimera trust eval` |

Every tool accepts an optional `compress=true` arg that routes oversized output through [chimeralang-mcp](https://github.com/fernandogarzaaa/chimeralang-mcp)'s `chimera_optimize` / `chimera_log_compress` before return.

## Why this is a plugin instead of a platform

Same code, two surfaces. The full GHOST-Chimera platform (docker, console, SaaS bits) is still available as a standalone project. This plugin lets users keep their existing Claude workflow and pull in GHOST capabilities **inside the chat** with one install — no separate UI, no separate process to learn.

## Compression at a glance

- **Build-time:** `skills/ghost/SKILL.md` is the chimera-compressed form of `SKILL.src.md` (~59% smaller, ~498 tokens saved per session activation).
- **Runtime:** any tool returning >800 chars can be flagged `compress=true` to invoke chimera on the way out.

## Requirements

- Python 3.11+
- `ghostchimera>=0.4.0` (pulled automatically)
- Optional: `chimeralang-mcp>=0.7.0` for runtime compression (`pip install ghost-mcp[compress]`)

## Smoke test

```bash
pip install -e .
python tools/smoke.py    # exercises all 18 tools' wiring
```

## License

MIT — see [LICENSE](LICENSE).
