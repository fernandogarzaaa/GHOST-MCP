"""Tests for ghost_mcp.server — permission helpers and boot_server."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ghost_mcp.config import DataSourceConfig, GhostMCPConfig, MCPConfig, PermissionsConfig
from ghost_mcp.server import (
    _all_allowed_paths,
    _build_mcp_server,
    _is_allowed,
    _is_excluded,
    boot_server,
)

# ── _is_excluded ──────────────────────────────────────────────────────────────


def test_is_excluded_matches_filename() -> None:
    assert _is_excluded(Path("/home/user/.env"), [".env"])


def test_is_excluded_matches_glob_pattern() -> None:
    assert _is_excluded(Path("/home/user/cert.key"), ["*.key"])


def test_is_excluded_matches_directory_part() -> None:
    assert _is_excluded(Path("/home/user/node_modules/pkg/index.js"), ["node_modules"])


def test_is_excluded_false_for_normal_file() -> None:
    assert not _is_excluded(Path("/home/user/docs/readme.txt"), ["*.key", ".env"])


def test_is_excluded_empty_patterns() -> None:
    assert not _is_excluded(Path("/home/user/.env"), [])


# ── _is_allowed ───────────────────────────────────────────────────────────────


def test_is_allowed_true_for_subpath(tmp_path: Path) -> None:
    allowed = tmp_path / "docs"
    allowed.mkdir()
    target = allowed / "note.txt"
    target.touch()
    assert _is_allowed(target, [str(allowed)])


def test_is_allowed_false_for_outside_path(tmp_path: Path) -> None:
    allowed = tmp_path / "docs"
    allowed.mkdir()
    outside = tmp_path / "secrets" / "key.pem"
    assert not _is_allowed(outside, [str(allowed)])


def test_is_allowed_true_for_directory_itself(tmp_path: Path) -> None:
    allowed = tmp_path / "work"
    allowed.mkdir()
    assert _is_allowed(allowed, [str(allowed)])


def test_is_allowed_multiple_dirs(tmp_path: Path) -> None:
    d1 = tmp_path / "a"
    d2 = tmp_path / "b"
    d1.mkdir()
    d2.mkdir()
    target = d2 / "file.txt"
    target.touch()
    assert _is_allowed(target, [str(d1), str(d2)])


# ── _all_allowed_paths ────────────────────────────────────────────────────────


def test_all_allowed_paths_empty_when_nothing_enabled() -> None:
    cfg = GhostMCPConfig()
    assert _all_allowed_paths(cfg) == []


def test_all_allowed_paths_includes_local_files(tmp_path: Path) -> None:
    cfg = GhostMCPConfig(
        profile_dir=str(tmp_path),
        data_sources=DataSourceConfig(local_files=True, local_file_paths=["/home/user/docs"]),
    )
    assert "/home/user/docs" in _all_allowed_paths(cfg)


def test_all_allowed_paths_includes_custom_paths(tmp_path: Path) -> None:
    cfg = GhostMCPConfig(
        profile_dir=str(tmp_path),
        data_sources=DataSourceConfig(custom_paths=["/home/user/notes"]),
    )
    assert "/home/user/notes" in _all_allowed_paths(cfg)


def test_all_allowed_paths_combines_both(tmp_path: Path) -> None:
    cfg = GhostMCPConfig(
        profile_dir=str(tmp_path),
        data_sources=DataSourceConfig(
            local_files=True,
            local_file_paths=["/a"],
            custom_paths=["/b"],
        ),
    )
    paths = _all_allowed_paths(cfg)
    assert "/a" in paths
    assert "/b" in paths


def test_all_allowed_paths_local_files_disabled(tmp_path: Path) -> None:
    cfg = GhostMCPConfig(
        profile_dir=str(tmp_path),
        data_sources=DataSourceConfig(local_files=False, local_file_paths=["/home/user/docs"]),
    )
    assert "/home/user/docs" not in _all_allowed_paths(cfg)


# ── _build_mcp_server — tools behaviour ──────────────────────────────────────


@pytest.fixture()
def file_tree(tmp_path: Path) -> Path:
    """Create a small file tree for tool tests."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "readme.txt").write_text("hello world")
    (docs / "notes.md").write_text("ghost context notes")
    (docs / ".env").write_text("SECRET=x")
    sub = docs / "sub"
    sub.mkdir()
    (sub / "deep.txt").write_text("deep content")
    return docs


def _make_cfg(profile_dir: str, docs_dir: str) -> GhostMCPConfig:
    return GhostMCPConfig(
        profile_dir=profile_dir,
        data_sources=DataSourceConfig(local_files=True, local_file_paths=[docs_dir]),
        permissions=PermissionsConfig(read_only=True, exclude_patterns=[".env", "*.key"]),
    )


class _MockFastMCP:
    """Minimal FastMCP stand-in that records registered tools."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._tools: dict[str, object] = {}

    def tool(self):
        def decorator(fn):
            self._tools[fn.__name__] = fn
            return fn

        return decorator

    def run(self, **kwargs) -> None:
        pass


def _build_server_with_mock(cfg: GhostMCPConfig) -> _MockFastMCP:
    mock_cls = _MockFastMCP
    with patch("ghost_mcp.server.FastMCP", mock_cls, create=True):
        # Patch the import inside _build_mcp_server
        fake_module = MagicMock()
        fake_module.FastMCP = mock_cls
        with patch.dict("sys.modules", {"mcp": fake_module, "mcp.server": fake_module, "mcp.server.fastmcp": fake_module}):
            return _build_mcp_server(cfg)


def test_build_mcp_server_registers_ghost_context(tmp_path: Path, file_tree: Path) -> None:
    cfg = _make_cfg(str(tmp_path), str(file_tree))
    server = _build_server_with_mock(cfg)
    assert "ghost_context" in server._tools


def test_build_mcp_server_registers_file_tools_when_paths_configured(tmp_path: Path, file_tree: Path) -> None:
    cfg = _make_cfg(str(tmp_path), str(file_tree))
    server = _build_server_with_mock(cfg)
    assert "list_files" in server._tools
    assert "read_file" in server._tools
    assert "search_files" in server._tools


def test_build_mcp_server_no_file_tools_when_no_paths(tmp_path: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_path))  # no paths
    server = _build_server_with_mock(cfg)
    assert "list_files" not in server._tools
    assert "read_file" not in server._tools


def test_ghost_context_tool_output(tmp_path: Path, file_tree: Path) -> None:
    cfg = _make_cfg(str(tmp_path), str(file_tree))
    server = _build_server_with_mock(cfg)
    result = server._tools["ghost_context"]()
    assert "Ghost MCP" in result
    assert cfg.profile_dir in result


def test_read_file_tool_returns_content(tmp_path: Path, file_tree: Path) -> None:
    cfg = _make_cfg(str(tmp_path), str(file_tree))
    server = _build_server_with_mock(cfg)
    path = str(file_tree / "readme.txt")
    result = server._tools["read_file"](path)
    assert "hello world" in result


def test_read_file_tool_excludes_env(tmp_path: Path, file_tree: Path) -> None:
    cfg = _make_cfg(str(tmp_path), str(file_tree))
    server = _build_server_with_mock(cfg)
    path = str(file_tree / ".env")
    result = server._tools["read_file"](path)
    assert "Error" in result
    assert "exclusion" in result


def test_read_file_tool_rejects_outside_path(tmp_path: Path, file_tree: Path) -> None:
    cfg = _make_cfg(str(tmp_path), str(file_tree))
    server = _build_server_with_mock(cfg)
    result = server._tools["read_file"]("/etc/passwd")
    assert "Error" in result
    assert "allowed" in result


def test_read_file_tool_missing_file(tmp_path: Path, file_tree: Path) -> None:
    cfg = _make_cfg(str(tmp_path), str(file_tree))
    server = _build_server_with_mock(cfg)
    result = server._tools["read_file"](str(file_tree / "nonexistent.txt"))
    assert "Error" in result
    assert "not found" in result


def test_search_files_finds_match(tmp_path: Path, file_tree: Path) -> None:
    cfg = _make_cfg(str(tmp_path), str(file_tree))
    server = _build_server_with_mock(cfg)
    result = server._tools["search_files"]("ghost context")
    assert "notes.md" in result


def test_search_files_no_match(tmp_path: Path, file_tree: Path) -> None:
    cfg = _make_cfg(str(tmp_path), str(file_tree))
    server = _build_server_with_mock(cfg)
    result = server._tools["search_files"]("zzz_not_present_xyz")
    assert "No files found" in result


def test_list_files_enumerates_directory(tmp_path: Path, file_tree: Path) -> None:
    cfg = _make_cfg(str(tmp_path), str(file_tree))
    server = _build_server_with_mock(cfg)
    result = server._tools["list_files"]()
    assert "readme.txt" in result


def test_list_files_excludes_env(tmp_path: Path, file_tree: Path) -> None:
    cfg = _make_cfg(str(tmp_path), str(file_tree))
    server = _build_server_with_mock(cfg)
    result = server._tools["list_files"]()
    assert ".env" not in result


def test_list_files_rejects_outside_dir(tmp_path: Path, file_tree: Path) -> None:
    cfg = _make_cfg(str(tmp_path), str(file_tree))
    server = _build_server_with_mock(cfg)
    result = server._tools["list_files"]("/etc")
    assert "not allowed" in result


# ── boot_server ───────────────────────────────────────────────────────────────


def test_boot_server_raises_when_no_backend(tmp_path: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_path))
    with (
        patch("ghost_mcp.server._get_ghostchimera_bridge", return_value=None),
        patch("ghost_mcp.server._build_mcp_server", side_effect=ImportError("no mcp")),
        pytest.raises(ImportError, match="No MCP server backend"),
    ):
        boot_server(cfg)


def test_boot_server_uses_ghostchimera_bridge_when_available(tmp_path: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_path), mcp=MCPConfig(transport="stdio"))
    mock_bridge = MagicMock()

    with patch("ghost_mcp.server._get_ghostchimera_bridge", return_value=mock_bridge):
        boot_server(cfg)

    mock_bridge.run.assert_called_once_with(transport="stdio", host="localhost", port=8765)


def test_boot_server_standalone_stdio(tmp_path: Path) -> None:
    cfg = GhostMCPConfig(profile_dir=str(tmp_path), mcp=MCPConfig(transport="stdio"))
    mock_server = MagicMock()

    with (
        patch("ghost_mcp.server._get_ghostchimera_bridge", return_value=None),
        patch("ghost_mcp.server._build_mcp_server", return_value=mock_server),
    ):
        boot_server(cfg)

    mock_server.run.assert_called_once_with(transport="stdio")


def test_boot_server_standalone_sse(tmp_path: Path) -> None:
    cfg = GhostMCPConfig(
        profile_dir=str(tmp_path),
        mcp=MCPConfig(transport="sse", host="0.0.0.0", port=9000),
    )
    mock_server = MagicMock()

    with (
        patch("ghost_mcp.server._get_ghostchimera_bridge", return_value=None),
        patch("ghost_mcp.server._build_mcp_server", return_value=mock_server),
    ):
        boot_server(cfg)

    mock_server.run.assert_called_once_with(transport="sse", host="0.0.0.0", port=9000)
