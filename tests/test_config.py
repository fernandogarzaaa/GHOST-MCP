"""Tests for ghost_mcp.config — save/load round-trip and defaults."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ghost_mcp.config import DataSourceConfig, GhostMCPConfig, MCPConfig, PermissionsConfig
from ghost_mcp.constants import DEFAULT_EXCLUDE_PATTERNS, VERSION

# ── DataSourceConfig ───────────────────────────────────────────────────────────


def test_data_source_defaults() -> None:
    ds = DataSourceConfig()
    assert ds.local_files is False
    assert ds.local_file_paths == []
    assert ds.browser_cache is False
    assert ds.browser_cache_targets == []
    assert ds.email is False
    assert ds.email_targets == []
    assert ds.calendar is False
    assert ds.calendar_targets == []
    assert ds.custom_paths == []


# ── PermissionsConfig ──────────────────────────────────────────────────────────


def test_permissions_defaults() -> None:
    perms = PermissionsConfig()
    assert perms.read_only is True
    assert set(perms.exclude_patterns) == set(DEFAULT_EXCLUDE_PATTERNS)


# ── MCPConfig ──────────────────────────────────────────────────────────────────


def test_mcp_defaults() -> None:
    mcp = MCPConfig()
    assert mcp.transport == "stdio"
    assert mcp.host == "localhost"
    assert mcp.port == 8765


# ── GhostMCPConfig defaults ────────────────────────────────────────────────────


def test_ghost_config_defaults() -> None:
    cfg = GhostMCPConfig()
    assert cfg.version == VERSION
    assert cfg.profile_dir.endswith(".ghost") or cfg.profile_dir == str(Path.home() / ".ghost")
    assert isinstance(cfg.data_sources, DataSourceConfig)
    assert isinstance(cfg.permissions, PermissionsConfig)
    assert isinstance(cfg.mcp, MCPConfig)


# ── Save / load round-trip ─────────────────────────────────────────────────────


@pytest.fixture()
def tmp_profile(tmp_path: Path) -> Path:
    return tmp_path / "ghost_test"


def test_save_creates_file(tmp_profile: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_profile))
    cfg.save()
    assert cfg.config_path.exists()


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    deep = tmp_path / "a" / "b" / "c"
    cfg = GhostMCPConfig(profile_dir=str(deep))
    cfg.save()
    assert cfg.config_path.exists()


def test_round_trip_minimal(tmp_profile: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_profile))
    cfg.save()
    loaded = GhostMCPConfig.load(str(tmp_profile))
    assert loaded.version == cfg.version
    assert loaded.profile_dir == cfg.profile_dir
    assert loaded.mcp.transport == "stdio"
    assert loaded.permissions.read_only is True


def test_round_trip_full(tmp_profile: Path) -> None:
    cfg = GhostMCPConfig(
        profile_dir=str(tmp_profile),
        data_sources=DataSourceConfig(
            local_files=True,
            local_file_paths=["/home/user/Documents", "/home/user/Projects"],
            browser_cache=True,
            browser_cache_targets=["chrome", "firefox"],
            email=True,
            email_targets=["apple_mail"],
            calendar=False,
            custom_paths=["/home/user/Notes"],
        ),
        permissions=PermissionsConfig(read_only=False, exclude_patterns=[".env", "*.key"]),
        mcp=MCPConfig(transport="sse", host="0.0.0.0", port=9000),
    )
    cfg.save()
    loaded = GhostMCPConfig.load(str(tmp_profile))

    assert loaded.data_sources.local_files is True
    assert loaded.data_sources.local_file_paths == ["/home/user/Documents", "/home/user/Projects"]
    assert loaded.data_sources.browser_cache is True
    assert loaded.data_sources.browser_cache_targets == ["chrome", "firefox"]
    assert loaded.data_sources.email is True
    assert loaded.data_sources.email_targets == ["apple_mail"]
    assert loaded.data_sources.calendar is False
    assert loaded.data_sources.custom_paths == ["/home/user/Notes"]
    assert loaded.permissions.read_only is False
    assert loaded.permissions.exclude_patterns == [".env", "*.key"]
    assert loaded.mcp.transport == "sse"
    assert loaded.mcp.host == "0.0.0.0"
    assert loaded.mcp.port == 9000


def test_saved_json_is_readable(tmp_profile: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_profile))
    cfg.save()
    with open(cfg.config_path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert "data_sources" in data
    assert "permissions" in data
    assert "mcp" in data


# ── exists / FileNotFoundError ─────────────────────────────────────────────────


def test_exists_false_when_no_config(tmp_path: Path) -> None:
    assert GhostMCPConfig.exists(str(tmp_path)) is False


def test_exists_true_after_save(tmp_profile: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_profile))
    cfg.save()
    assert GhostMCPConfig.exists(str(tmp_profile)) is True


def test_load_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="ghost-mcp init"):
        GhostMCPConfig.load(str(tmp_path))


# ── config_path / directory properties ────────────────────────────────────────


def test_config_path_property(tmp_profile: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_profile))
    assert cfg.config_path == tmp_profile / "mcp.json"


def test_memory_dir_property(tmp_profile: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_profile))
    assert cfg.memory_dir == tmp_profile / "memory"


def test_model_dir_property(tmp_profile: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_profile))
    assert cfg.model_dir == tmp_profile / "models"
