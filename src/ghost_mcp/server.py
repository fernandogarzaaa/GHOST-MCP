"""Ghost MCP server — boot_server exposes ghost tools via the MCP protocol.

Architecture
------------
1. If ``ghostchimera.mcp.GhostMCPBridge`` is available it is used as-is
   (full RAG + mini-model experience).
2. Otherwise a standalone FastMCP server is built from the config, exposing
   a core set of ghost tools for file access and context.

Tools exposed by the standalone server
---------------------------------------
ghost_context         — configuration summary and accessible paths
list_files(directory) — list files in ghost-accessible directories
read_file(path)       — read a single file's contents
search_files(query)   — find files containing a query string
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ghost_mcp.config import GhostMCPConfig


# ── Permission helpers ─────────────────────────────────────────────────────────


def _is_excluded(path: Path, patterns: list[str]) -> bool:
    """Return True if any component of *path* matches an exclusion pattern."""
    for part in path.parts:
        for pattern in patterns:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


def _is_allowed(path: Path, allowed_dirs: list[str]) -> bool:
    """Return True if *path* is contained within one of *allowed_dirs*."""
    resolved = path.resolve()
    for d in allowed_dirs:
        allowed = Path(d).expanduser().resolve()
        try:
            resolved.relative_to(allowed)
            return True
        except ValueError:
            continue
    return False


def _all_allowed_paths(cfg: GhostMCPConfig) -> list[str]:
    """Return every path ghost is configured to access."""
    paths: list[str] = []
    ds = cfg.data_sources
    if ds.local_files:
        paths.extend(ds.local_file_paths)
    if ds.custom_paths:
        paths.extend(ds.custom_paths)
    return paths


# ── Standalone MCP server ──────────────────────────────────────────────────────


def _build_mcp_server(cfg: GhostMCPConfig):  # type: ignore[return]
    """Build a FastMCP server instance wired to *cfg*.

    Raises ``ImportError`` when the ``mcp`` package is not installed.
    """
    from mcp.server.fastmcp import FastMCP  # type: ignore[import]

    server = FastMCP("Ghost MCP")
    allowed_paths = _all_allowed_paths(cfg)
    exclude_patterns = cfg.permissions.exclude_patterns

    @server.tool()
    def ghost_context() -> str:
        """Return a summary of the Ghost MCP configuration and accessible data sources."""
        lines = [
            "Ghost MCP — Personal AI Proxy",
            f"Profile directory : {cfg.profile_dir}",
            f"Transport         : {cfg.mcp.transport}",
            f"Read-only         : {cfg.permissions.read_only}",
            "",
            "Accessible paths:",
        ]
        if allowed_paths:
            lines.extend(f"  {p}" for p in allowed_paths)
        else:
            lines.append("  (none configured — run ghost-mcp init)")
        return "\n".join(lines)

    if allowed_paths:

        @server.tool()
        def list_files(directory: str = "") -> str:
            """List files accessible to Ghost in *directory* (or all accessible dirs)."""
            target_dirs = [directory] if directory else allowed_paths
            results: list[str] = []
            for d in target_dirs:
                p = Path(d).expanduser().resolve()
                if not p.exists():
                    results.append(f"[not found] {d}")
                    continue
                if not _is_allowed(p, allowed_paths):
                    results.append(f"[not allowed] {d}")
                    continue
                try:
                    for child in sorted(p.iterdir()):
                        if _is_excluded(child, exclude_patterns):
                            continue
                        kind = "DIR " if child.is_dir() else "FILE"
                        results.append(f"{kind}  {child}")
                except PermissionError:
                    results.append(f"[permission denied] {p}")
            return "\n".join(results) if results else "(no files found)"

        @server.tool()
        def read_file(path: str) -> str:
            """Read the contents of a file that Ghost is allowed to access."""
            p = Path(path).expanduser().resolve()
            if not p.exists():
                return f"Error: file not found: {path}"
            if not _is_allowed(p, allowed_paths):
                return f"Error: path not in ghost-allowed directories: {path}"
            if _is_excluded(p, exclude_patterns):
                return f"Error: path matches an exclusion pattern: {path}"
            if not p.is_file():
                return f"Error: not a regular file: {path}"
            try:
                return p.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                return f"Error reading file: {exc}"

        @server.tool()
        def search_files(query: str, directory: str = "") -> str:
            """Search for files whose contents contain *query* (case-insensitive)."""
            target_dirs = [directory] if directory else allowed_paths
            matches: list[str] = []
            needle = query.lower()
            for d in target_dirs:
                p = Path(d).expanduser().resolve()
                if not p.exists() or not _is_allowed(p, allowed_paths):
                    continue
                for file_path in sorted(p.rglob("*")):
                    if not file_path.is_file():
                        continue
                    if _is_excluded(file_path, exclude_patterns):
                        continue
                    try:
                        if needle in file_path.read_text(encoding="utf-8", errors="ignore").lower():
                            matches.append(str(file_path))
                    except OSError:
                        continue
            if not matches:
                return f"No files found containing: {query!r}"
            return "Files containing {!r}:\n{}".format(query, "\n".join(f"  {m}" for m in matches))

    return server


# ── Entry point ────────────────────────────────────────────────────────────────


def _get_ghostchimera_bridge(cfg: GhostMCPConfig):
    """Return a ghostchimera MCP bridge instance, or ``None`` if unavailable."""
    try:
        import ghostchimera.mcp as gc_mcp  # type: ignore[import]

        if hasattr(gc_mcp, "GhostMCPBridge"):
            return gc_mcp.GhostMCPBridge(cfg)
    except ImportError:
        pass
    return None


def boot_server(cfg: GhostMCPConfig) -> None:
    """Start the Ghost MCP server.

    Tries ghostchimera's full bridge first; falls back to the built-in
    standalone server when ghostchimera is not available or has no bridge.

    Parameters
    ----------
    cfg:
        Loaded ``GhostMCPConfig`` instance (transport, port, and data
        source settings are read from here).
    """
    # Prefer ghostchimera's full bridge when available
    bridge = _get_ghostchimera_bridge(cfg)
    if bridge is not None:
        bridge.run(transport=cfg.mcp.transport, host=cfg.mcp.host, port=cfg.mcp.port)
        return

    # Standalone FastMCP server
    try:
        server = _build_mcp_server(cfg)
    except ImportError as exc:
        raise ImportError(
            "No MCP server backend available. "
            "Install ghost-mcp[mcp] to use the standalone server, "
            "or ghost-mcp[full] for the full ghost experience."
        ) from exc

    if cfg.mcp.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport="sse", host=cfg.mcp.host, port=cfg.mcp.port)
