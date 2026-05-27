"""Tests for ghost_mcp.cli.serve — run_serve behaviour."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ghost_mcp.cli.serve import _check_ghostchimera, _check_server_available, run_serve
from ghost_mcp.config import GhostMCPConfig

# ── _check_ghostchimera ───────────────────────────────────────────────────────


def test_check_ghostchimera_false_when_not_installed() -> None:
    with patch.dict("sys.modules", {"ghostchimera": None, "ghostchimera.mcp": None}):
        assert _check_ghostchimera() is False


# ── _check_server_available ───────────────────────────────────────────────────


def test_check_server_available_false_when_nothing_installed() -> None:
    # Simulate both ghostchimera.mcp and mcp.server.fastmcp missing
    with (
        patch("ghost_mcp.cli.serve._check_ghostchimera", return_value=False),
        patch.dict("sys.modules", {"mcp": None, "mcp.server": None, "mcp.server.fastmcp": None}),
    ):
        # FastMCP import will raise ImportError because module is None
        assert _check_server_available() is False


def test_check_server_available_true_when_ghostchimera_present() -> None:
    with patch("ghost_mcp.cli.serve._check_ghostchimera", return_value=True):
        assert _check_server_available() is True


# ── run_serve — no config ─────────────────────────────────────────────────────


def test_run_serve_no_config_exits(tmp_path: Path, capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run_serve(profile_dir=str(tmp_path))
    assert exc_info.value.code == 1
    out = capsys.readouterr().out
    assert "ghost-mcp init" in out


# ── run_serve — no backend ────────────────────────────────────────────────────


def test_run_serve_no_backend_exits(tmp_path: Path, capsys) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_path / "ghost"))
    cfg.save()
    with (
        patch("ghost_mcp.cli.serve._check_server_available", return_value=False),
        pytest.raises(SystemExit) as exc_info,
    ):
        run_serve(profile_dir=cfg.profile_dir)
    assert exc_info.value.code == 1
    out = capsys.readouterr().out
    assert "ghost-mcp[mcp]" in out or "ghost-mcp[full]" in out


# ── run_serve — success path ──────────────────────────────────────────────────


def test_run_serve_calls_boot_server(tmp_path: Path, capsys) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_path / "ghost"))
    cfg.save()

    mock_boot = MagicMock()
    with (
        patch("ghost_mcp.cli.serve._check_server_available", return_value=True),
        patch("ghost_mcp.server.boot_server", mock_boot),
    ):
        run_serve(profile_dir=cfg.profile_dir)

    mock_boot.assert_called_once()
    called_cfg = mock_boot.call_args[0][0]
    assert called_cfg.profile_dir == cfg.profile_dir


def test_run_serve_transport_override(tmp_path: Path, capsys) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_path / "ghost"))
    cfg.save()

    mock_boot = MagicMock()
    with (
        patch("ghost_mcp.cli.serve._check_server_available", return_value=True),
        patch("ghost_mcp.server.boot_server", mock_boot),
    ):
        run_serve(profile_dir=cfg.profile_dir, transport="sse")

    called_cfg = mock_boot.call_args[0][0]
    assert called_cfg.mcp.transport == "sse"


def test_run_serve_port_override(tmp_path: Path, capsys) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_path / "ghost"))
    cfg.save()

    mock_boot = MagicMock()
    with (
        patch("ghost_mcp.cli.serve._check_server_available", return_value=True),
        patch("ghost_mcp.server.boot_server", mock_boot),
    ):
        run_serve(profile_dir=cfg.profile_dir, port=9876)

    called_cfg = mock_boot.call_args[0][0]
    assert called_cfg.mcp.port == 9876


def test_run_serve_keyboard_interrupt_handled(tmp_path: Path, capsys) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_path / "ghost"))
    cfg.save()

    with (
        patch("ghost_mcp.cli.serve._check_server_available", return_value=True),
        patch("ghost_mcp.server.boot_server", side_effect=KeyboardInterrupt),
    ):
        # Should not raise — KeyboardInterrupt is caught
        run_serve(profile_dir=cfg.profile_dir)

    out = capsys.readouterr().out
    assert "stopped" in out.lower()
