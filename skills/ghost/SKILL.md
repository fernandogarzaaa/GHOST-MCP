---
name: ghost
description: Use Ghost-Chimera capabilities — local-first agent orchestration, Trust Runtime, MiniMind personal memory, and PR/production-gap automation. Triggers when the user asks about Ghost, GHOST-Chimera, Chimera Pilot, MiniMind, Trust Runtime, Standing Orders, or wants to run an objective against their local agent.
---

# GHOST Skill — Routing Matrix
Ghost is a local-first agent orchestrator with Chimera Pilot scheduling, 27 model providers, durable Trust Runtime, MiniMind personal memory, and a Ghost Console browser UI.
| User wants Ghost to remember a fact for future runs | `ghost_teach` (Q&A pair) |
| User points at files/dirs/emails to feed personal memory | `ghost_ingest` (kind=file/directory/email_file/raw_email/document) |
| Durable runs, approvals, OTel traces, eval baselines | `ghost_trust` action=status/runs/trace/eval/eval-cases |
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
## When NOT to use Ghost tools
- File edits the user can do via Edit/Write → use those tools directly.
- Pure search/grep of the current repo → use Bash/grep, not `ghost_search` (which searches Ghost memory, not the repo).
