"""Ghost MCP CLI — entry point for the `ghost-mcp` command.

Subcommands
-----------
ghost-mcp init    Run the onboarding wizard (configure data sources & guardrails)
ghost-mcp status  Display the current configuration
ghost-mcp serve   Start the Ghost MCP server
"""

from __future__ import annotations

import argparse
import sys

from ghost_mcp import __version__

# ── Subcommand handlers ────────────────────────────────────────────────────────


def _cmd_init(args: argparse.Namespace) -> None:
    from ghost_mcp.cli.wizard import run_wizard

    run_wizard(
        profile_dir=args.profile_dir or None,
        yes=args.yes,
    )


def _cmd_status(args: argparse.Namespace) -> None:
    from ghost_mcp.cli.status import run_status

    run_status(profile_dir=args.profile_dir or None)


def _cmd_serve(args: argparse.Namespace) -> None:
    from ghost_mcp.cli.serve import run_serve

    run_serve(
        profile_dir=args.profile_dir or None,
        transport=args.transport or None,
        port=args.port or None,
    )


# ── Argument parser ────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ghost-mcp",
        description=(
            "Ghost MCP — personal AI proxy for MCP-compatible platforms.\n\n"
            "Ghost reads your local data, builds a contextual understanding of who\n"
            "you are, and feeds that context to Claude, Codex, and other AI models."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"ghost-mcp {__version__}",
    )

    subs = parser.add_subparsers(dest="command", metavar="<command>")

    # ── init ──────────────────────────────────────────────────────────────────
    p_init = subs.add_parser(
        "init",
        help="run the onboarding wizard",
        description=(
            "Interactive 7-step wizard that lets you configure which personal data\n"
            "sources Ghost is allowed to read, with per-source guardrails.\n\n"
            "Re-run at any time to update your configuration."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_init.add_argument(
        "--profile-dir",
        metavar="PATH",
        default=None,
        help="override the ghost profile directory (default: ~/.ghost)",
    )
    p_init.add_argument(
        "-y",
        "--yes",
        action="store_true",
        default=False,
        help="skip the final save-confirmation prompt",
    )
    p_init.set_defaults(func=_cmd_init)

    # ── status ────────────────────────────────────────────────────────────────
    p_status = subs.add_parser(
        "status",
        help="show current configuration",
        description="Display the current Ghost MCP configuration and data-source permissions.",
    )
    p_status.add_argument(
        "--profile-dir",
        metavar="PATH",
        default=None,
        help="ghost profile directory to inspect (default: ~/.ghost)",
    )
    p_status.set_defaults(func=_cmd_status)

    # ── serve ─────────────────────────────────────────────────────────────────
    p_serve = subs.add_parser(
        "serve",
        help="start the Ghost MCP server",
        description=(
            "Boot the Ghost MCP server and expose ghost tools to the connected\n"
            "MCP host (Claude Desktop, Windsurf, Continue, etc.).\n\n"
            "Requires: pip install ghost-mcp[mcp]"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_serve.add_argument(
        "--profile-dir",
        metavar="PATH",
        default=None,
        help="ghost profile directory to use (default: ~/.ghost)",
    )
    p_serve.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default=None,
        help="override transport from config",
    )
    p_serve.add_argument(
        "--port",
        type=int,
        default=None,
        metavar="PORT",
        help="override SSE port from config",
    )
    p_serve.set_defaults(func=_cmd_serve)

    return parser


# ── Entry point ────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    """Main entry point for the ``ghost-mcp`` command."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        # No subcommand given — print help and exit
        parser.print_help()
        sys.exit(0)

    args.func(args)
