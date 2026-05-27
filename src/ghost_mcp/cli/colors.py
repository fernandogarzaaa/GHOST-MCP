"""ANSI color utilities for Ghost MCP CLI.

Mirrors the convention used in Ghost-Chimera's control_plane/colors.py.
"""

from __future__ import annotations


class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"


def color(text: str, fg: str, bold: bool = False) -> str:
    prefix = Colors.BOLD if bold else ""
    return f"{prefix}{fg}{text}{Colors.RESET}"


def print_banner() -> None:
    lines = [
        r"  ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗    ███╗   ███╗ ██████╗██████╗ ",
        r" ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝    ████╗ ████║██╔════╝██╔══██╗",
        r" ██║  ███╗███████║██║   ██║███████╗   ██║       ██╔████╔██║██║     ██████╔╝",
        r" ██║   ██║██╔══██║██║   ██║╚════██║   ██║       ██║╚██╔╝██║██║     ██╔═══╝ ",
        r" ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║       ██║ ╚═╝ ██║╚██████╗██║     ",
        r"  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝       ╚═╝     ╚═╝ ╚═════╝╚═╝     ",
    ]
    print()
    for line in lines:
        print(color(line, Colors.CYAN))


def print_header(title: str, step: int | None = None, total: int | None = None) -> None:
    print()
    sep = "═" * 56
    print(color(sep, Colors.DIM))
    if step is not None and total is not None:
        prefix = color(f"  STEP {step} of {total}", Colors.CYAN, bold=True)
        print(f"{prefix}  {Colors.DIM}—{Colors.RESET}  {Colors.BOLD}{title}{Colors.RESET}")
    else:
        print(f"  {color(title, Colors.CYAN, bold=True)}")
    print(color(sep, Colors.DIM))


def print_info(msg: str) -> None:
    print(f"  {Colors.DIM}{msg}{Colors.RESET}")


def print_success(msg: str) -> None:
    print(f"  {Colors.GREEN}✓  {Colors.RESET}{msg}")


def print_warning(msg: str) -> None:
    print(f"  {Colors.YELLOW}!  {Colors.RESET}{msg}")


def print_error(msg: str) -> None:
    print(f"  {Colors.RED}✗  {Colors.RESET}{msg}", flush=True)


def print_skip(msg: str) -> None:
    print(f"  {Colors.DIM}✗  {msg}{Colors.RESET}")
