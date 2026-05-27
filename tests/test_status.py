"""Tests for ghost_mcp.cli.status — run_status output."""

from __future__ import annotations

from pathlib import Path

import pytest

from ghost_mcp.cli.status import run_status
from ghost_mcp.config import DataSourceConfig, GhostMCPConfig, MCPConfig, PermissionsConfig

# ── No config → exit 1 ───────────────────────────────────────────────────────


def test_run_status_no_config_exits(tmp_path: Path, capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run_status(profile_dir=str(tmp_path))
    assert exc_info.value.code == 1
    err = capsys.readouterr().out
    assert "ghost-mcp init" in err


# ── With valid config ─────────────────────────────────────────────────────────


@pytest.fixture()
def saved_cfg(tmp_path: Path) -> GhostMCPConfig:
    cfg = GhostMCPConfig(
        profile_dir=str(tmp_path / "ghost"),
        data_sources=DataSourceConfig(
            local_files=True,
            local_file_paths=["/home/user/Documents"],
            browser_cache=False,
            email=True,
            email_targets=["apple_mail"],
            calendar=False,
        ),
        permissions=PermissionsConfig(read_only=True),
        mcp=MCPConfig(transport="stdio"),
    )
    cfg.save()
    return cfg


def test_run_status_shows_config_path(saved_cfg: GhostMCPConfig, capsys) -> None:
    run_status(profile_dir=saved_cfg.profile_dir)
    out = capsys.readouterr().out
    assert "mcp.json" in out


def test_run_status_shows_transport(saved_cfg: GhostMCPConfig, capsys) -> None:
    run_status(profile_dir=saved_cfg.profile_dir)
    out = capsys.readouterr().out
    assert "stdio" in out


def test_run_status_shows_enabled_local_files(saved_cfg: GhostMCPConfig, capsys) -> None:
    run_status(profile_dir=saved_cfg.profile_dir)
    out = capsys.readouterr().out
    assert "/home/user/Documents" in out


def test_run_status_shows_disabled_browser_cache(saved_cfg: GhostMCPConfig, capsys) -> None:
    run_status(profile_dir=saved_cfg.profile_dir)
    out = capsys.readouterr().out
    assert "Browser cache" in out


def test_run_status_shows_email_client(saved_cfg: GhostMCPConfig, capsys) -> None:
    run_status(profile_dir=saved_cfg.profile_dir)
    out = capsys.readouterr().out
    assert "Apple Mail" in out


def test_run_status_shows_read_only(saved_cfg: GhostMCPConfig, capsys) -> None:
    run_status(profile_dir=saved_cfg.profile_dir)
    out = capsys.readouterr().out
    assert "read-only" in out


def test_run_status_sse_shows_port(tmp_path: Path, capsys) -> None:
    cfg = GhostMCPConfig(
        profile_dir=str(tmp_path / "ghost"),
        mcp=MCPConfig(transport="sse", port=9999),
    )
    cfg.save()
    run_status(profile_dir=cfg.profile_dir)
    out = capsys.readouterr().out
    assert "9999" in out


def test_run_status_shows_exclusion_count(saved_cfg: GhostMCPConfig, capsys) -> None:
    run_status(profile_dir=saved_cfg.profile_dir)
    out = capsys.readouterr().out
    assert "pattern" in out


def test_run_status_memory_not_yet_created(saved_cfg: GhostMCPConfig, capsys) -> None:
    run_status(profile_dir=saved_cfg.profile_dir)
    out = capsys.readouterr().out
    assert "not yet created" in out


def test_run_status_memory_exists(saved_cfg: GhostMCPConfig, capsys) -> None:
    mem_dir = Path(saved_cfg.profile_dir) / "memory"
    mem_dir.mkdir()
    (mem_dir / "note.txt").write_text("hello")
    run_status(profile_dir=saved_cfg.profile_dir)
    out = capsys.readouterr().out
    assert "1 file" in out
