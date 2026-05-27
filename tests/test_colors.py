"""Tests for ghost_mcp.cli.colors — ANSI helpers."""

from __future__ import annotations

import io
import sys

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

# ── color() ───────────────────────────────────────────────────────────────────


def test_color_wraps_text() -> None:
    result = color("hello", Colors.CYAN)
    assert "hello" in result
    assert Colors.CYAN in result
    assert Colors.RESET in result


def test_color_bold_prepends_bold_code() -> None:
    result = color("hi", Colors.GREEN, bold=True)
    assert Colors.BOLD in result
    assert Colors.GREEN in result
    assert "hi" in result


def test_color_not_bold_excludes_bold_code() -> None:
    result = color("hi", Colors.RED, bold=False)
    assert Colors.BOLD not in result


# ── print helpers write to stdout ────────────────────────────────────────────


def _capture(fn, *args, **kwargs) -> str:
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn(*args, **kwargs)
    finally:
        sys.stdout = old
    return buf.getvalue()


def test_print_info_outputs_text() -> None:
    out = _capture(print_info, "some info")
    assert "some info" in out


def test_print_success_contains_check() -> None:
    out = _capture(print_success, "done")
    assert "✓" in out
    assert "done" in out


def test_print_warning_contains_exclamation() -> None:
    out = _capture(print_warning, "careful")
    assert "!" in out
    assert "careful" in out


def test_print_error_contains_cross() -> None:
    out = _capture(print_error, "bad")
    assert "✗" in out
    assert "bad" in out


def test_print_skip_contains_cross() -> None:
    out = _capture(print_skip, "skipped")
    assert "✗" in out
    assert "skipped" in out


def test_print_header_contains_title() -> None:
    out = _capture(print_header, "My Title")
    assert "My Title" in out


def test_print_header_with_step_shows_step_info() -> None:
    out = _capture(print_header, "Step Title", step=3, total=7)
    assert "3" in out
    assert "7" in out
    assert "Step Title" in out


def test_print_banner_outputs_ascii_art() -> None:
    out = _capture(print_banner)
    # Banner contains "GHOST" and "MCP" in ASCII art block letters
    assert len(out) > 100
