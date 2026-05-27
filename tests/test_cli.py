"""Tests for ghost_mcp.cli — argument parser and subcommand dispatch."""

from __future__ import annotations

import pytest

from ghost_mcp.cli import _build_parser, main

# ── Parser structure ──────────────────────────────────────────────────────────


def test_parser_has_version(capsys) -> None:
    parser = _build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--version"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "ghost-mcp" in out
    assert "0.1.0" in out


def test_parser_no_subcommand_exits_zero(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 0


def test_parser_init_help(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["init", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "wizard" in out.lower() or "init" in out.lower()


def test_parser_status_help(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["status", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "status" in out.lower() or "configuration" in out.lower()


def test_parser_serve_help(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["serve", "--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "serve" in out.lower() or "server" in out.lower()


def test_parser_init_accepts_profile_dir() -> None:
    parser = _build_parser()
    args = parser.parse_args(["init", "--profile-dir", "/tmp/myprofile"])
    assert args.profile_dir == "/tmp/myprofile"


def test_parser_init_yes_flag() -> None:
    parser = _build_parser()
    args = parser.parse_args(["init", "-y"])
    assert args.yes is True


def test_parser_serve_transport_option() -> None:
    parser = _build_parser()
    args = parser.parse_args(["serve", "--transport", "sse"])
    assert args.transport == "sse"


def test_parser_serve_port_option() -> None:
    parser = _build_parser()
    args = parser.parse_args(["serve", "--port", "9000"])
    assert args.port == 9000


def test_parser_status_profile_dir() -> None:
    parser = _build_parser()
    args = parser.parse_args(["status", "--profile-dir", "/tmp/x"])
    assert args.profile_dir == "/tmp/x"
