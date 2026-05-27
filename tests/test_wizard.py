"""Tests for ghost_mcp.cli.wizard — helper functions and non-interactive path."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import patch

from ghost_mcp.cli.wizard import (
    _print_noninteractive_guidance,
    _prompt_path_list,
    _show_next_steps,
    _show_review,
    is_interactive,
    run_wizard,
)
from ghost_mcp.config import DataSourceConfig, GhostMCPConfig, MCPConfig, PermissionsConfig

# ── is_interactive ────────────────────────────────────────────────────────────


def test_is_interactive_false_when_stdin_is_none() -> None:
    with patch.object(sys, "stdin", None):
        assert is_interactive() is False


def test_is_interactive_false_when_not_a_tty() -> None:
    fake_stdin = io.StringIO()
    with patch.object(sys, "stdin", fake_stdin):
        assert is_interactive() is False


# ── run_wizard — non-interactive ──────────────────────────────────────────────


def test_run_wizard_non_interactive_prints_guidance(capsys) -> None:
    with patch("ghost_mcp.cli.wizard.is_interactive", return_value=False):
        run_wizard()
    out = capsys.readouterr().out
    assert "mcp.json" in out or "ghost-mcp init" in out


def test_run_wizard_non_interactive_does_not_save(tmp_path: Path) -> None:
    profile = tmp_path / "ghost"
    with patch("ghost_mcp.cli.wizard.is_interactive", return_value=False):
        run_wizard(profile_dir=str(profile))
    assert not (profile / "mcp.json").exists()


# ── _show_review ──────────────────────────────────────────────────────────────


def _capture(fn, *args, **kwargs) -> str:
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn(*args, **kwargs)
    finally:
        sys.stdout = old
    return buf.getvalue()


def _make_full_cfg(profile_dir: str) -> GhostMCPConfig:
    return GhostMCPConfig(
        profile_dir=profile_dir,
        data_sources=DataSourceConfig(
            local_files=True,
            local_file_paths=["/home/user/Docs"],
            browser_cache=True,
            browser_cache_targets=["chrome"],
            email=True,
            email_targets=["apple_mail"],
            calendar=True,
            calendar_targets=["apple_calendar"],
            custom_paths=["/home/user/Notes"],
        ),
        permissions=PermissionsConfig(read_only=False),
        mcp=MCPConfig(transport="sse", port=9000),
    )


def test_show_review_local_files_listed(tmp_path: Path) -> None:
    cfg = _make_full_cfg(str(tmp_path))
    out = _capture(_show_review, cfg)
    assert "/home/user/Docs" in out


def test_show_review_browser_cache_listed(tmp_path: Path) -> None:
    cfg = _make_full_cfg(str(tmp_path))
    out = _capture(_show_review, cfg)
    assert "Google Chrome" in out


def test_show_review_email_listed(tmp_path: Path) -> None:
    cfg = _make_full_cfg(str(tmp_path))
    out = _capture(_show_review, cfg)
    assert "Apple Mail" in out


def test_show_review_calendar_listed(tmp_path: Path) -> None:
    cfg = _make_full_cfg(str(tmp_path))
    out = _capture(_show_review, cfg)
    assert "Apple Calendar" in out


def test_show_review_read_write_shown(tmp_path: Path) -> None:
    cfg = _make_full_cfg(str(tmp_path))
    out = _capture(_show_review, cfg)
    assert "read-write" in out


def test_show_review_sse_transport_shown(tmp_path: Path) -> None:
    cfg = _make_full_cfg(str(tmp_path))
    out = _capture(_show_review, cfg)
    assert "sse" in out
    assert "9000" in out


def test_show_review_disabled_sources_skipped(tmp_path: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_path))  # all sources disabled
    out = _capture(_show_review, cfg)
    assert "disabled" in out or "✗" in out


# ── _show_next_steps ──────────────────────────────────────────────────────────


def test_show_next_steps_contains_serve_command(tmp_path: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_path))
    out = _capture(_show_next_steps, cfg)
    assert "ghost-mcp serve" in out


def test_show_next_steps_contains_claude_config(tmp_path: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_path))
    out = _capture(_show_next_steps, cfg)
    assert "Claude" in out


# ── _print_noninteractive_guidance ────────────────────────────────────────────


def test_noninteractive_guidance_mentions_mcp_json(capsys) -> None:
    _print_noninteractive_guidance()
    out = capsys.readouterr().out
    assert "mcp.json" in out


def test_noninteractive_guidance_shows_example(capsys) -> None:
    _print_noninteractive_guidance()
    out = capsys.readouterr().out
    assert "local_files" in out


# ── _prompt_path_list ─────────────────────────────────────────────────────────


def test_prompt_path_list_parses_comma_separated(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "/a/b, /c/d")
    result = _prompt_path_list("label", [])
    assert result == ["/a/b", "/c/d"]


def test_prompt_path_list_strips_whitespace(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "  /foo  ,  /bar  ")
    result = _prompt_path_list("label", [])
    assert result == ["/foo", "/bar"]


def test_prompt_path_list_uses_default_on_empty(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "")
    result = _prompt_path_list("label", ["/default/path"])
    assert result == ["/default/path"]
