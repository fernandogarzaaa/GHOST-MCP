"""Ghost MCP onboarding wizard — `ghost-mcp init`.

A 7-step interactive setup that lets users configure which personal data
sources Ghost is allowed to read, with per-source guardrails.

Steps
-----
1. Ghost profile directory
2. Local files
3. Browser cache
4. Email
5. Calendar
6. Custom paths
7. Permissions & MCP transport

Each step is a standalone function so individual sections can be tested
or re-run independently.  Patterned after Ghost-Chimera's setup_wizard.py.
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path

from ghost_mcp.cli.colors import (
    Colors,
    color,
    print_banner,
    print_error,
    print_header,
    print_info,
    print_skip,
    print_success,
    print_warning,
)
from ghost_mcp.config import DataSourceConfig, GhostMCPConfig, MCPConfig, PermissionsConfig
from ghost_mcp.constants import (
    BROWSER_TARGETS,
    CALENDAR_TARGETS,
    DEFAULT_EXCLUDE_PATTERNS,
    DEFAULT_PROFILE_DIR,
    EMAIL_TARGETS,
    VERSION,
)

_TOTAL_STEPS = 7


# ── Low-level prompt helpers ───────────────────────────────────────────────────


def is_interactive() -> bool:
    """Return True when stdin is a usable interactive TTY."""
    stdin = getattr(sys, "stdin", None)
    if stdin is None:
        return False
    try:
        return bool(stdin.isatty())
    except Exception:
        return False


def _prompt(question: str, default: str = "") -> str:
    """Display *question* and return stripped user input (or *default*)."""
    display = f"{question} [{default}]: " if default else f"{question}: "
    try:
        value = input(color(display, Colors.YELLOW))
        return value.strip() or default
    except (KeyboardInterrupt, EOFError):
        print()
        print_warning("Setup cancelled.")
        sys.exit(1)


def _prompt_yn(question: str, default: bool = True) -> bool:
    """Prompt for yes/no, return *default* on empty input."""
    hint = "Y/n" if default else "y/N"
    while True:
        try:
            raw = input(color(f"  {question} [{hint}]: ", Colors.YELLOW)).strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            print_warning("Setup cancelled.")
            sys.exit(1)
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print_error("Please enter 'y' or 'n'")


def _prompt_choice(question: str, choices: list[str], default: int = 0) -> int:
    """Show a numbered list and return the selected index."""
    print()
    print(f"  {question}")
    for i, ch in enumerate(choices):
        marker = color(f"  > {ch}", Colors.GREEN) if i == default else f"    {ch}"
        print(marker)
    print(f"  {Colors.DIM}Enter for default  ·  Ctrl+C to exit{Colors.RESET}")
    while True:
        try:
            raw = input(color(f"  Select [1-{len(choices)}]: ", Colors.DIM)).strip()
            if not raw:
                return default
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return idx
            print_error(f"Enter a number between 1 and {len(choices)}")
        except ValueError:
            print_error("Enter a number")
        except (KeyboardInterrupt, EOFError):
            print()
            print_warning("Setup cancelled.")
            sys.exit(1)


def _prompt_path_list(label: str, defaults: list[str]) -> list[str]:
    """Ask for a comma-separated list of paths, return as a list."""
    default_str = ", ".join(defaults) if defaults else ""
    print(f"\n  {label}")
    raw = _prompt(
        "  Directories (comma-separated)",
        default=default_str,
    )
    return [p.strip() for p in raw.split(",") if p.strip()]


def _prompt_multi_select(
    label: str,
    options: dict[str, str],
    defaults: list[str],
) -> list[str]:
    """Ask yes/no for each option; return the list of selected keys."""
    print(f"\n  {label}")
    selected = []
    for key, display in options.items():
        default = key in defaults
        if _prompt_yn(display, default=default):
            selected.append(key)
    return selected


# ── Wizard steps ───────────────────────────────────────────────────────────────


def _step_profile_dir(existing: GhostMCPConfig | None) -> str:
    print_header("Ghost Profile Directory", step=1, total=_TOTAL_STEPS)
    print()
    print_info("Ghost stores its memory, model weights, and settings in a")
    print_info("profile directory.  All data stays on your machine.")
    default = existing.profile_dir if existing else str(DEFAULT_PROFILE_DIR)
    raw = _prompt("\n  Profile directory", default=default)
    return str(Path(raw).expanduser().resolve())


def _step_local_files(existing: GhostMCPConfig | None) -> tuple[bool, list[str]]:
    print_header("Local Files", step=2, total=_TOTAL_STEPS)
    print()
    print_info("Ghost can scan your local files to understand your projects,")
    print_info("notes, and documents.")
    print()
    print_warning("Only the directories you specify will be scanned.")

    default_enabled = existing.data_sources.local_files if existing else False
    enabled = _prompt_yn("\n  Enable local file access?", default=default_enabled)
    if not enabled:
        return False, []

    default_paths = (
        existing.data_sources.local_file_paths
        if (existing and existing.data_sources.local_file_paths)
        else [str(Path.home() / "Documents"), str(Path.home() / "Desktop")]
    )
    paths = _prompt_path_list(
        "Which directories should Ghost scan?",
        default_paths,
    )
    return True, paths


def _step_browser_cache(existing: GhostMCPConfig | None) -> tuple[bool, list[str]]:
    print_header("Browser Cache", step=3, total=_TOTAL_STEPS)
    print()
    print_info("Ghost can read your browser history to understand your")
    print_info("interests and research patterns.")
    print()
    print_warning("History is read locally — nothing is sent to any external server.")

    default_enabled = existing.data_sources.browser_cache if existing else False
    enabled = _prompt_yn("\n  Enable browser cache access?", default=default_enabled)
    if not enabled:
        return False, []

    defaults = existing.data_sources.browser_cache_targets if existing else []
    selected = _prompt_multi_select(
        "Which browsers should Ghost access?",
        BROWSER_TARGETS,
        defaults=defaults,
    )
    return True, selected


def _step_email(existing: GhostMCPConfig | None) -> tuple[bool, list[str]]:
    print_header("Email", step=4, total=_TOTAL_STEPS)
    print()
    print_info("Ghost can read your local email to understand your communication")
    print_info("style, contacts, and professional context.")
    print()
    print_warning("Only locally stored mail is accessed.  No cloud login required.")

    default_enabled = existing.data_sources.email if existing else False
    enabled = _prompt_yn("\n  Enable email access?", default=default_enabled)
    if not enabled:
        return False, []

    defaults = existing.data_sources.email_targets if existing else []
    selected = _prompt_multi_select(
        "Which email clients should Ghost access?",
        EMAIL_TARGETS,
        defaults=defaults,
    )
    return True, selected


def _step_calendar(existing: GhostMCPConfig | None) -> tuple[bool, list[str]]:
    print_header("Calendar", step=5, total=_TOTAL_STEPS)
    print()
    print_info("Ghost can read your calendar to understand your schedule,")
    print_info("commitments, and time patterns.")
    print()
    print_warning("Only locally synced calendar data is accessed.")

    default_enabled = existing.data_sources.calendar if existing else False
    enabled = _prompt_yn("\n  Enable calendar access?", default=default_enabled)
    if not enabled:
        return False, []

    defaults = existing.data_sources.calendar_targets if existing else []
    selected = _prompt_multi_select(
        "Which calendar sources should Ghost access?",
        CALENDAR_TARGETS,
        defaults=defaults,
    )
    return True, selected


def _step_custom_paths(existing: GhostMCPConfig | None) -> list[str]:
    print_header("Custom Paths", step=6, total=_TOTAL_STEPS)
    print()
    print_info("Add any other files or directories Ghost should read.")
    print_info("Examples: ~/Notes, ~/Obsidian, ~/Dropbox/Work, ~/Journals")

    has_existing = bool(existing and existing.data_sources.custom_paths)
    enabled = _prompt_yn("\n  Add custom paths?", default=has_existing)
    if not enabled:
        return []

    defaults = existing.data_sources.custom_paths if existing else []
    paths = _prompt_path_list("Custom paths:", defaults)
    return paths


def _step_permissions_and_transport(
    existing: GhostMCPConfig | None,
) -> tuple[PermissionsConfig, MCPConfig]:
    print_header("Permissions & Transport", step=7, total=_TOTAL_STEPS)

    # ── Read-only mode ─────────────────────────────────────────────────────────
    print()
    print_info("Ghost operates in read-only mode by default.")
    print_info("In this mode it can never write, delete, or modify your data.")
    read_only_default = existing.permissions.read_only if existing else True
    read_only = _prompt_yn(
        "\n  Keep read-only mode? (recommended)",
        default=read_only_default,
    )
    if not read_only:
        print_warning("  Read-write mode enabled — Ghost may modify files it scans.")

    # ── Exclusion patterns ─────────────────────────────────────────────────────
    print()
    print_info("Sensitive files are skipped by default:")
    sample = "  " + ",  ".join(DEFAULT_EXCLUDE_PATTERNS[:8]) + ",  …"
    print_info(sample)
    use_defaults = _prompt_yn(
        "\n  Use default exclusion patterns? (recommended)",
        default=True,
    )
    if use_defaults:
        exclude_patterns = list(DEFAULT_EXCLUDE_PATTERNS)
    elif existing:
        exclude_patterns = existing.permissions.exclude_patterns
    else:
        exclude_patterns = list(DEFAULT_EXCLUDE_PATTERNS)

    # ── MCP transport ──────────────────────────────────────────────────────────
    print()
    print_info("How should Ghost MCP communicate with your AI host?")
    transport_idx = _prompt_choice(
        "Transport:",
        [
            "stdio  —  Claude Desktop, Continue, Windsurf  (recommended)",
            "sse    —  persistent HTTP server for remote / advanced setups",
        ],
        default=0 if (not existing or existing.mcp.transport == "stdio") else 1,
    )
    transport = "stdio" if transport_idx == 0 else "sse"

    port = existing.mcp.port if existing else 8765
    if transport == "sse":
        port_str = _prompt("\n  SSE port", default=str(port))
        try:
            port = int(port_str)
        except ValueError:
            print_warning("  Invalid port — using 8765")
            port = 8765

    permissions = PermissionsConfig(read_only=read_only, exclude_patterns=exclude_patterns)
    mcp_cfg = MCPConfig(transport=transport, port=port)
    return permissions, mcp_cfg


# ── Review ─────────────────────────────────────────────────────────────────────


def _show_review(cfg: GhostMCPConfig) -> None:
    print_header("Review Your Configuration")
    print()
    print(f"  Profile directory : {color(cfg.profile_dir, Colors.CYAN)}")
    print()
    print("  Data sources:")

    ds = cfg.data_sources
    if ds.local_files:
        print_success(f"Local files    → {', '.join(ds.local_file_paths) or 'default'}")
    else:
        print_skip("Local files    — disabled")

    if ds.browser_cache:
        labels = [BROWSER_TARGETS[k] for k in ds.browser_cache_targets if k in BROWSER_TARGETS]
        print_success(f"Browser cache  → {', '.join(labels) or 'none selected'}")
    else:
        print_skip("Browser cache  — disabled")

    if ds.email:
        labels = [EMAIL_TARGETS[k] for k in ds.email_targets if k in EMAIL_TARGETS]
        print_success(f"Email          → {', '.join(labels) or 'none selected'}")
    else:
        print_skip("Email          — disabled")

    if ds.calendar:
        labels = [CALENDAR_TARGETS[k] for k in ds.calendar_targets if k in CALENDAR_TARGETS]
        print_success(f"Calendar       → {', '.join(labels) or 'none selected'}")
    else:
        print_skip("Calendar       — disabled")

    if ds.custom_paths:
        print_success(f"Custom paths   → {', '.join(ds.custom_paths)}")
    else:
        print_skip("Custom paths   — none")

    print()
    mode = color("read-only", Colors.GREEN) if cfg.permissions.read_only else color("read-write", Colors.RED)
    print(f"  Permissions  : {mode},  {len(cfg.permissions.exclude_patterns)} exclusion pattern(s)")
    print(f"  Transport    : {color(cfg.mcp.transport, Colors.CYAN)}", end="")
    if cfg.mcp.transport == "sse":
        print(f"  (port {cfg.mcp.port})", end="")
    print()


# ── Next steps ─────────────────────────────────────────────────────────────────


def _show_next_steps(cfg: GhostMCPConfig) -> None:
    print_header("Next Steps")
    sys_platform = platform.system()

    print()
    print("  Ghost MCP is ready.  Add it to your AI platform:\n")

    if sys_platform == "Darwin":
        claude_path = "~/Library/Application Support/Claude/claude_desktop_config.json"
    elif sys_platform == "Windows":
        claude_path = "%APPDATA%\\Claude\\claude_desktop_config.json"
    else:
        claude_path = "~/.config/Claude/claude_desktop_config.json"

    print(color("  ── Claude Desktop ────────────────────────────────────", Colors.DIM))
    print(f"  Config: {color(claude_path, Colors.CYAN)}\n")
    snippet = (
        '  {\n'
        '    "mcpServers": {\n'
        '      "ghost": {\n'
        '        "command": "ghost-mcp",\n'
        '        "args": ["serve"]\n'
        '      }\n'
        '    }\n'
        '  }'
    )
    print(color(snippet, Colors.DIM))
    print()

    print(color("  ── Continue / Windsurf ───────────────────────────────", Colors.DIM))
    print('  Add to your mcpServers block:')
    print(color('  "ghost": { "command": "ghost-mcp", "args": ["serve"] }', Colors.DIM))
    print()

    print(color("  ── Useful commands ───────────────────────────────────", Colors.DIM))
    print(f"  {color('ghost-mcp status', Colors.CYAN)}    — show current configuration")
    print(f"  {color('ghost-mcp init',   Colors.CYAN)}      — re-run this wizard")
    print(f"  {color('ghost-mcp serve',  Colors.CYAN)}     — start the Ghost MCP server")
    print()


# ── Non-interactive fallback ───────────────────────────────────────────────────


def _print_noninteractive_guidance() -> None:
    print()
    print(color("  Ghost MCP Setup — Non-interactive mode", Colors.CYAN, bold=True))
    print()
    print("  The interactive wizard cannot run here (no TTY detected).")
    print()
    print("  Configure Ghost MCP by creating a JSON file at:")
    print(f"  {color('~/.ghost/mcp.json', Colors.CYAN)}")
    print()
    print("  Minimal example:")
    example = (
        '  {\n'
        '    "profile_dir": "~/.ghost",\n'
        '    "data_sources": {\n'
        '      "local_files": true,\n'
        '      "local_file_paths": ["~/Documents"]\n'
        '    },\n'
        '    "permissions": { "read_only": true },\n'
        '    "mcp": { "transport": "stdio" }\n'
        '  }'
    )
    print(color(example, Colors.DIM))
    print()
    print("  Or run 'ghost-mcp init' in an interactive terminal.")
    print()


# ── Main wizard entry point ────────────────────────────────────────────────────


def run_wizard(profile_dir: str | None = None, yes: bool = False) -> None:
    """Run the full Ghost MCP onboarding wizard.

    Parameters
    ----------
    profile_dir:
        Override the Ghost profile directory.  When *None* the user is asked
        during Step 1 (defaulting to ``~/.ghost``).
    yes:
        Skip the final save-confirmation prompt.
    """
    if not is_interactive():
        _print_noninteractive_guidance()
        return

    # Banner
    print_banner()
    print()
    print(color(f"  Ghost MCP Setup Wizard  v{VERSION}", Colors.BOLD))
    print()
    print("  Ghost is your personal AI proxy.  It runs locally, learns from your")
    print("  data, and feeds context to Claude, Codex, and other AI platforms via MCP.")
    print()
    print(color("  You decide exactly what Ghost can see.", Colors.BOLD))

    # Check for existing config
    existing: GhostMCPConfig | None = None
    check_dir = profile_dir or str(DEFAULT_PROFILE_DIR)
    if GhostMCPConfig.exists(check_dir):
        try:
            existing = GhostMCPConfig.load(check_dir)
            print()
            print_warning(f"Existing configuration found at: {existing.config_path}")
            if not _prompt_yn("  Reconfigure Ghost MCP?", default=False):
                print("\n  Setup cancelled.  Run `ghost-mcp status` to review your config.")
                return
        except Exception:
            existing = None

    print()
    if not _prompt_yn("  Ready to begin?", default=True):
        print("\n  Setup cancelled.")
        return

    # ── Run steps ──────────────────────────────────────────────────────────────
    resolved_profile = _step_profile_dir(existing)
    if profile_dir:
        resolved_profile = str(Path(profile_dir).expanduser().resolve())

    local_enabled, local_paths = _step_local_files(existing)
    browser_enabled, browser_targets = _step_browser_cache(existing)
    email_enabled, email_targets = _step_email(existing)
    calendar_enabled, calendar_targets = _step_calendar(existing)
    custom_paths = _step_custom_paths(existing)
    permissions, mcp_cfg = _step_permissions_and_transport(existing)

    cfg = GhostMCPConfig(
        profile_dir=resolved_profile,
        data_sources=DataSourceConfig(
            local_files=local_enabled,
            local_file_paths=local_paths,
            browser_cache=browser_enabled,
            browser_cache_targets=browser_targets,
            email=email_enabled,
            email_targets=email_targets,
            calendar=calendar_enabled,
            calendar_targets=calendar_targets,
            custom_paths=custom_paths,
        ),
        permissions=permissions,
        mcp=mcp_cfg,
    )

    # ── Review & confirm ───────────────────────────────────────────────────────
    _show_review(cfg)

    print()
    if not yes and not _prompt_yn("  Save this configuration?", default=True):
        print("\n  Setup cancelled.  No changes were saved.")
        return

    # ── Persist ────────────────────────────────────────────────────────────────
    try:
        cfg.save()
        print()
        print_success(f"Configuration saved to: {color(str(cfg.config_path), Colors.CYAN)}")
    except OSError as exc:
        print_error(f"Failed to save configuration: {exc}")
        sys.exit(1)

    _show_next_steps(cfg)
