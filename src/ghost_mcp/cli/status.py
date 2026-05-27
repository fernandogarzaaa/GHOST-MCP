"""ghost-mcp status — display current Ghost MCP configuration."""

from __future__ import annotations

import sys
from pathlib import Path

from ghost_mcp.cli.colors import Colors, color, print_error, print_header, print_info, print_skip, print_success
from ghost_mcp.config import GhostMCPConfig
from ghost_mcp.constants import (
    BROWSER_TARGETS,
    CALENDAR_TARGETS,
    DEFAULT_PROFILE_DIR,
    EMAIL_TARGETS,
)


def run_status(profile_dir: str | None = None) -> None:
    """Print the current Ghost MCP configuration to stdout."""
    check_dir = profile_dir or str(DEFAULT_PROFILE_DIR)

    if not GhostMCPConfig.exists(check_dir):
        print_error("No Ghost MCP configuration found.")
        print_info(f"Expected: {Path(check_dir) / 'mcp.json'}")
        print_info("Run `ghost-mcp init` to set up.")
        sys.exit(1)

    try:
        cfg = GhostMCPConfig.load(check_dir)
    except Exception as exc:
        print_error(f"Failed to load configuration: {exc}")
        sys.exit(1)

    print_header("Ghost MCP — Status")
    print()
    print(f"  Config file  : {color(str(cfg.config_path), Colors.CYAN)}")
    print(f"  Version      : {cfg.version}")
    print(f"  Profile dir  : {cfg.profile_dir}")

    memory_dir = cfg.memory_dir
    memory_status = (
        color(f"exists ({sum(1 for _ in memory_dir.rglob('*') if _.is_file())} file(s))", Colors.GREEN)
        if memory_dir.exists()
        else color("not yet created", Colors.DIM)
    )
    print(f"  Memory dir   : {memory_status}")

    # ── Data sources ───────────────────────────────────────────────────────────
    print()
    print(color("  Data Sources", Colors.CYAN, bold=True))

    ds = cfg.data_sources
    if ds.local_files:
        print_success(f"Local files    → {', '.join(ds.local_file_paths) or 'none configured'}")
    else:
        print_skip("Local files    — disabled")

    if ds.browser_cache:
        labels = [BROWSER_TARGETS.get(k, k) for k in ds.browser_cache_targets]
        print_success(f"Browser cache  → {', '.join(labels) or 'none selected'}")
    else:
        print_skip("Browser cache  — disabled")

    if ds.email:
        labels = [EMAIL_TARGETS.get(k, k) for k in ds.email_targets]
        print_success(f"Email          → {', '.join(labels) or 'none selected'}")
    else:
        print_skip("Email          — disabled")

    if ds.calendar:
        labels = [CALENDAR_TARGETS.get(k, k) for k in ds.calendar_targets]
        print_success(f"Calendar       → {', '.join(labels) or 'none selected'}")
    else:
        print_skip("Calendar       — disabled")

    if ds.custom_paths:
        print_success(f"Custom paths   → {', '.join(ds.custom_paths)}")
    else:
        print_skip("Custom paths   — none")

    # ── Permissions ────────────────────────────────────────────────────────────
    print()
    print(color("  Permissions", Colors.CYAN, bold=True))
    mode = color("read-only", Colors.GREEN) if cfg.permissions.read_only else color("read-write ⚠", Colors.YELLOW)
    print(f"  Mode         : {mode}")
    print(f"  Exclusions   : {len(cfg.permissions.exclude_patterns)} pattern(s)")

    # ── MCP ────────────────────────────────────────────────────────────────────
    print()
    print(color("  MCP Server", Colors.CYAN, bold=True))
    print(f"  Transport    : {color(cfg.mcp.transport, Colors.CYAN)}")
    if cfg.mcp.transport == "sse":
        print(f"  Port         : {cfg.mcp.port}")

    print()
    print_info("To reconfigure:  ghost-mcp init")
    print_info("To start server: ghost-mcp serve")
    print()
