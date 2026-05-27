"""ghost-mcp serve — start the Ghost MCP server.

When ghostchimera[mcp] is installed this boots the full ghost bridge and
exposes tools to the connected MCP host (e.g. Claude Desktop).

When ghostchimera is not installed, a helpful installation message is shown.
"""

from __future__ import annotations

import sys

from ghost_mcp.cli.colors import Colors, color, print_error, print_info, print_success, print_warning
from ghost_mcp.config import GhostMCPConfig
from ghost_mcp.constants import DEFAULT_PROFILE_DIR


def _check_ghostchimera() -> bool:
    """Return True when ghostchimera with MCP support is importable."""
    try:
        import ghostchimera.mcp  # noqa: F401

        return True
    except ImportError:
        return False


def _check_server_available() -> bool:
    """Return True when at least one MCP server backend is importable."""
    if _check_ghostchimera():
        return True
    try:
        from mcp.server.fastmcp import FastMCP  # noqa: F401

        return True
    except ImportError:
        return False


def run_serve(
    profile_dir: str | None = None,
    transport: str | None = None,
    port: int | None = None,
) -> None:
    """Start the Ghost MCP server.

    Parameters
    ----------
    profile_dir:
        Override the ghost profile directory.
    transport:
        Override the transport mode from config (``"stdio"`` or ``"sse"``).
    port:
        Override the SSE port from config.
    """
    check_dir = profile_dir or str(DEFAULT_PROFILE_DIR)

    # Load config (required before serving)
    if not GhostMCPConfig.exists(check_dir):
        print_error("No Ghost MCP configuration found.")
        print_info("Run `ghost-mcp init` first to configure your ghost.")
        sys.exit(1)

    try:
        cfg = GhostMCPConfig.load(check_dir)
    except Exception as exc:
        print_error(f"Failed to load configuration: {exc}")
        sys.exit(1)

    # Apply CLI overrides
    if transport:
        cfg.mcp.transport = transport
    if port:
        cfg.mcp.port = port

    # Check at least one server backend is available
    if not _check_server_available():
        print_warning("No MCP server backend is installed.")
        print()
        print("  Ghost MCP needs at least one of the following:")
        print()
        print(f"  {color('pip install ghost-mcp[mcp]', Colors.CYAN)}    — standalone MCP server")
        print(f"  {color('pip install ghost-mcp[full]', Colors.CYAN)}   — full ghost experience")
        print()
        sys.exit(1)

    # Import and boot the ghost bridge (requires ghostchimera[mcp])
    try:
        from ghost_mcp.server import boot_server  # type: ignore[import]
    except ImportError:
        print_error("ghost_mcp.server is not available — the package may be incomplete.")
        print_info("Please reinstall: pip install ghost-mcp[mcp]")
        sys.exit(1)

    print_success(f"Starting Ghost MCP server  [transport={cfg.mcp.transport}]")
    if cfg.mcp.transport == "sse":
        print_info(f"Listening on {cfg.mcp.host}:{cfg.mcp.port}")

    try:
        boot_server(cfg)
    except KeyboardInterrupt:
        print()
        print_info("Ghost MCP server stopped.")
