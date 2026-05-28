#!/usr/bin/env bash
# GHOST-MCP SessionStart hook: announce capability surface.
cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"GHOST-MCP active. 18 tools available (ghost_run, ghost_teach, ghost_ingest, ghost_search, ghost_trust, ghost_review_pr, ghost_gaps, ghost_doctor, ghost_models, ghost_autonomy, ghost_minimind, ghost_console, ghost_capabilities, ghost_path, ghost_orders, ghost_eval, ghost_memory_status, ghost_preview_context). Pass compress=true to route large outputs through chimeralang-mcp."}}
EOF
