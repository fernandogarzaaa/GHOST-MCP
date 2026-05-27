"""ghost-mcp install-claude — auto-configure Ghost MCP in Claude Desktop.

Reads the Claude Desktop config JSON (creating it when absent), merges in the
ghost-mcp server entry, and writes it back.  The user is shown a diff-style
summary of what changed.
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

from ghost_mcp.cli.colors import Colors, color, print_error, print_info, print_success, print_warning

# ── Platform helpers ───────────────────────────────────────────────────────────


def _default_claude_config_path() -> Path:
    """Return the platform-specific Claude Desktop config path."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if system == "Windows":
        appdata = Path.home() / "AppData" / "Roaming"
        return appdata / "Claude" / "claude_desktop_config.json"
    # Linux / other
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


# ── Config helpers ─────────────────────────────────────────────────────────────


def _load_claude_config(path: Path) -> dict:
    """Load and return the Claude Desktop config, or an empty dict if absent/corrupt."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return {}
        return data
    except (OSError, json.JSONDecodeError):
        return {}


def _build_ghost_entry(transport: str, port: int | None) -> dict:
    """Return the mcpServers entry for ghost-mcp."""
    if transport == "sse":
        return {
            "command": "ghost-mcp",
            "args": ["serve", "--transport", "sse"] + (["--port", str(port)] if port else []),
        }
    return {
        "command": "ghost-mcp",
        "args": ["serve"],
    }


def _merge_ghost_entry(config: dict, entry: dict) -> tuple[dict, bool]:
    """Merge *entry* into config["mcpServers"]["ghost"], returning (new_config, changed)."""
    config.setdefault("mcpServers", {})
    existing = config["mcpServers"].get("ghost")
    if existing == entry:
        return config, False
    config["mcpServers"]["ghost"] = entry
    return config, True


def _write_claude_config(path: Path, config: dict) -> None:
    """Write *config* to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
        fh.write("\n")


# ── Main command ───────────────────────────────────────────────────────────────


def run_install_claude(
    config_path: str | None = None,
    transport: str = "stdio",
    port: int | None = None,
    dry_run: bool = False,
) -> None:
    """Install Ghost MCP into Claude Desktop's config file.

    Parameters
    ----------
    config_path:
        Override the Claude Desktop config path.
    transport:
        MCP transport to configure (``"stdio"`` or ``"sse"``).
    port:
        SSE port — only used when *transport* is ``"sse"``.
    dry_run:
        When ``True`` print what would change without writing anything.
    """
    target = Path(config_path).expanduser().resolve() if config_path else _default_claude_config_path()

    print_info(f"Claude Desktop config: {color(str(target), Colors.CYAN)}")

    existing_config = _load_claude_config(target)
    if not target.exists():
        print_warning("Config file not found — it will be created.")

    ghost_entry = _build_ghost_entry(transport, port)
    new_config, changed = _merge_ghost_entry(existing_config, ghost_entry)

    if not changed:
        print_success("Ghost MCP is already configured in Claude Desktop.")
        _print_current_entry(new_config["mcpServers"]["ghost"])
        return

    # Show what will be written
    print()
    print(color("  Ghost MCP entry:", Colors.CYAN, bold=True))
    snippet = json.dumps({"ghost": ghost_entry}, indent=2)
    for line in snippet.splitlines():
        print(f"    {color(line, Colors.DIM)}")
    print()

    if dry_run:
        print_warning("Dry run — no changes written.")
        return

    try:
        _write_claude_config(target, new_config)
    except OSError as exc:
        print_error(f"Failed to write config: {exc}")
        sys.exit(1)

    print_success(f"Ghost MCP installed at: {color(str(target), Colors.CYAN)}")
    print()
    print_info("Restart Claude Desktop for the changes to take effect.")
    print()
    print(color("  ── Verify ───────────────────────────────────────────────", Colors.DIM))
    print(f"  {color('ghost-mcp status', Colors.CYAN)}   — confirm server config")
    print(f"  {color('ghost-mcp serve',  Colors.CYAN)}    — test the server manually")
    print()


def _print_current_entry(entry: dict) -> None:
    """Print the current ghost entry in the Claude Desktop config."""
    print()
    print(color("  Current entry:", Colors.DIM))
    snippet = json.dumps({"ghost": entry}, indent=2)
    for line in snippet.splitlines():
        print(f"    {color(line, Colors.DIM)}")
    print()
    print_info("Re-run with --transport or --port to update it.")
    print()
