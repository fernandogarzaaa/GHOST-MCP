"""Tests for ghost_mcp.cli.install — install-claude subcommand."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ghost_mcp.cli.install import (
    _build_ghost_entry,
    _default_claude_config_path,
    _load_claude_config,
    _merge_ghost_entry,
    _write_claude_config,
    run_install_claude,
)

# ── _default_claude_config_path ───────────────────────────────────────────────


def test_default_path_darwin() -> None:
    with patch("platform.system", return_value="Darwin"):
        p = _default_claude_config_path()
    assert "Library" in str(p)
    assert "Claude" in str(p)
    assert p.name == "claude_desktop_config.json"


def test_default_path_windows() -> None:
    with patch("platform.system", return_value="Windows"):
        p = _default_claude_config_path()
    assert "Roaming" in str(p) or "AppData" in str(p)
    assert p.name == "claude_desktop_config.json"


def test_default_path_linux() -> None:
    with patch("platform.system", return_value="Linux"):
        p = _default_claude_config_path()
    assert ".config" in str(p)
    assert p.name == "claude_desktop_config.json"


def test_default_path_unknown_os() -> None:
    with patch("platform.system", return_value="FreeBSD"):
        p = _default_claude_config_path()
    assert p.name == "claude_desktop_config.json"


# ── _load_claude_config ───────────────────────────────────────────────────────


def test_load_returns_empty_dict_when_file_missing(tmp_path: Path) -> None:
    result = _load_claude_config(tmp_path / "nonexistent.json")
    assert result == {}


def test_load_returns_empty_dict_on_bad_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    assert _load_claude_config(bad) == {}


def test_load_returns_empty_dict_when_top_level_not_dict(tmp_path: Path) -> None:
    f = tmp_path / "list.json"
    f.write_text("[1, 2, 3]", encoding="utf-8")
    assert _load_claude_config(f) == {}


def test_load_returns_existing_config(tmp_path: Path) -> None:
    cfg = {"mcpServers": {"other": {"command": "other-cmd", "args": []}}}
    f = tmp_path / "claude_desktop_config.json"
    f.write_text(json.dumps(cfg), encoding="utf-8")
    assert _load_claude_config(f) == cfg


def test_load_returns_empty_dict_on_os_error(tmp_path: Path) -> None:
    f = tmp_path / "no_perms.json"
    f.write_text("{}", encoding="utf-8")
    f.chmod(0o000)
    try:
        result = _load_claude_config(f)
        assert result == {}
    finally:
        f.chmod(0o644)


# ── _build_ghost_entry ────────────────────────────────────────────────────────


def test_build_entry_stdio() -> None:
    entry = _build_ghost_entry("stdio", None)
    assert entry == {"command": "ghost-mcp", "args": ["serve"]}


def test_build_entry_sse_no_port() -> None:
    entry = _build_ghost_entry("sse", None)
    assert entry["args"] == ["serve", "--transport", "sse"]


def test_build_entry_sse_with_port() -> None:
    entry = _build_ghost_entry("sse", 9000)
    assert "--port" in entry["args"]
    assert "9000" in entry["args"]


# ── _merge_ghost_entry ────────────────────────────────────────────────────────


def test_merge_creates_mcp_servers_key() -> None:
    config, changed = _merge_ghost_entry({}, {"command": "ghost-mcp", "args": ["serve"]})
    assert "mcpServers" in config
    assert changed is True


def test_merge_adds_ghost_to_existing_servers() -> None:
    base = {"mcpServers": {"other": {"command": "x", "args": []}}}
    entry = {"command": "ghost-mcp", "args": ["serve"]}
    config, changed = _merge_ghost_entry(base, entry)
    assert "other" in config["mcpServers"]
    assert "ghost" in config["mcpServers"]
    assert changed is True


def test_merge_unchanged_when_entry_identical() -> None:
    entry = {"command": "ghost-mcp", "args": ["serve"]}
    base = {"mcpServers": {"ghost": entry}}
    config, changed = _merge_ghost_entry(base, entry)
    assert changed is False


def test_merge_changed_when_entry_updated() -> None:
    old_entry = {"command": "ghost-mcp", "args": ["serve"]}
    new_entry = {"command": "ghost-mcp", "args": ["serve", "--transport", "sse"]}
    base = {"mcpServers": {"ghost": old_entry}}
    config, changed = _merge_ghost_entry(base, new_entry)
    assert changed is True
    assert config["mcpServers"]["ghost"] == new_entry


def test_merge_preserves_unrelated_keys() -> None:
    base = {"someKey": "someValue", "mcpServers": {}}
    entry = {"command": "ghost-mcp", "args": ["serve"]}
    config, _ = _merge_ghost_entry(base, entry)
    assert config["someKey"] == "someValue"


# ── _write_claude_config ──────────────────────────────────────────────────────


def test_write_creates_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "nested" / "claude_desktop_config.json"
    _write_claude_config(target, {"mcpServers": {}})
    assert target.exists()


def test_write_produces_valid_json(tmp_path: Path) -> None:
    target = tmp_path / "config.json"
    data = {"mcpServers": {"ghost": {"command": "ghost-mcp", "args": ["serve"]}}}
    _write_claude_config(target, data)
    with open(target) as fh:
        loaded = json.load(fh)
    assert loaded == data


def test_write_ends_with_newline(tmp_path: Path) -> None:
    target = tmp_path / "config.json"
    _write_claude_config(target, {})
    assert target.read_text().endswith("\n")


# ── run_install_claude ────────────────────────────────────────────────────────


def test_run_install_creates_config(tmp_path: Path, capsys) -> None:
    target = tmp_path / "claude_desktop_config.json"
    run_install_claude(config_path=str(target))
    assert target.exists()
    config = json.loads(target.read_text())
    assert config["mcpServers"]["ghost"]["command"] == "ghost-mcp"
    out = capsys.readouterr().out
    assert "installed" in out.lower() or "Ghost MCP" in out


def test_run_install_preserves_existing_servers(tmp_path: Path) -> None:
    target = tmp_path / "claude_desktop_config.json"
    existing = {"mcpServers": {"other-tool": {"command": "other", "args": []}}}
    target.write_text(json.dumps(existing), encoding="utf-8")
    run_install_claude(config_path=str(target))
    config = json.loads(target.read_text())
    assert "other-tool" in config["mcpServers"]
    assert "ghost" in config["mcpServers"]


def test_run_install_sse_transport(tmp_path: Path) -> None:
    target = tmp_path / "claude_desktop_config.json"
    run_install_claude(config_path=str(target), transport="sse", port=9001)
    config = json.loads(target.read_text())
    args = config["mcpServers"]["ghost"]["args"]
    assert "--transport" in args
    assert "sse" in args
    assert "--port" in args
    assert "9001" in args


def test_run_install_dry_run_does_not_write(tmp_path: Path) -> None:
    target = tmp_path / "claude_desktop_config.json"
    run_install_claude(config_path=str(target), dry_run=True)
    assert not target.exists()


def test_run_install_dry_run_prints_warning(tmp_path: Path, capsys) -> None:
    target = tmp_path / "claude_desktop_config.json"
    run_install_claude(config_path=str(target), dry_run=True)
    out = capsys.readouterr().out
    assert "dry run" in out.lower() or "Dry run" in out


def test_run_install_already_configured_is_idempotent(tmp_path: Path, capsys) -> None:
    target = tmp_path / "claude_desktop_config.json"
    # Install once
    run_install_claude(config_path=str(target))
    capsys.readouterr()
    # Install again — should report already configured, not error
    run_install_claude(config_path=str(target))
    out = capsys.readouterr().out
    assert "already configured" in out.lower() or "already" in out.lower()


def test_run_install_updates_existing_ghost_entry(tmp_path: Path) -> None:
    target = tmp_path / "claude_desktop_config.json"
    old = {"mcpServers": {"ghost": {"command": "ghost-mcp", "args": ["serve", "--transport", "sse"]}}}
    target.write_text(json.dumps(old), encoding="utf-8")
    # Switch back to stdio
    run_install_claude(config_path=str(target), transport="stdio")
    config = json.loads(target.read_text())
    assert config["mcpServers"]["ghost"]["args"] == ["serve"]


def test_run_install_bad_json_config_recovers(tmp_path: Path) -> None:
    target = tmp_path / "claude_desktop_config.json"
    target.write_text("corrupted", encoding="utf-8")
    # Should not raise — treats corrupt file as empty config
    run_install_claude(config_path=str(target))
    config = json.loads(target.read_text())
    assert "ghost" in config["mcpServers"]


def test_run_install_exits_on_write_error(tmp_path: Path) -> None:
    target = tmp_path / "claude_desktop_config.json"
    with patch("ghost_mcp.cli.install._write_claude_config", side_effect=OSError("disk full")), pytest.raises(SystemExit):
        run_install_claude(config_path=str(target))


# ── CLI integration ───────────────────────────────────────────────────────────


def test_cli_install_claude_subcommand(tmp_path: Path) -> None:
    from ghost_mcp.cli import main

    target = tmp_path / "claude_desktop_config.json"
    main(["install-claude", "--config-path", str(target)])
    assert target.exists()


def test_cli_install_claude_dry_run_flag(tmp_path: Path) -> None:
    from ghost_mcp.cli import main

    target = tmp_path / "config.json"
    main(["install-claude", "--config-path", str(target), "--dry-run"])
    assert not target.exists()


def test_cli_install_claude_sse_flags(tmp_path: Path) -> None:
    from ghost_mcp.cli import main

    target = tmp_path / "config.json"
    main(["install-claude", "--config-path", str(target), "--transport", "sse", "--port", "8888"])
    config = json.loads(target.read_text())
    assert "8888" in config["mcpServers"]["ghost"]["args"]
