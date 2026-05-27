"""Ghost MCP configuration — dataclasses backed by a local JSON file."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ghost_mcp.constants import CONFIG_FILENAME, DEFAULT_EXCLUDE_PATTERNS, DEFAULT_PROFILE_DIR, VERSION

# ── Sub-configs ────────────────────────────────────────────────────────────────


@dataclass
class DataSourceConfig:
    """Which personal data sources the ghost is allowed to read."""

    local_files: bool = False
    local_file_paths: list[str] = field(default_factory=list)

    browser_cache: bool = False
    browser_cache_targets: list[str] = field(default_factory=list)

    email: bool = False
    email_targets: list[str] = field(default_factory=list)

    calendar: bool = False
    calendar_targets: list[str] = field(default_factory=list)

    custom_paths: list[str] = field(default_factory=list)


@dataclass
class PermissionsConfig:
    """Guardrails that govern how the ghost may interact with the filesystem."""

    read_only: bool = True
    exclude_patterns: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE_PATTERNS))


@dataclass
class MCPConfig:
    """Transport and network settings for the MCP server."""

    transport: str = "stdio"  # "stdio" | "sse"
    host: str = "localhost"
    port: int = 8765


# ── Root config ────────────────────────────────────────────────────────────────


@dataclass
class GhostMCPConfig:
    """Root configuration object for Ghost MCP."""

    version: str = VERSION
    profile_dir: str = str(DEFAULT_PROFILE_DIR)
    data_sources: DataSourceConfig = field(default_factory=DataSourceConfig)
    permissions: PermissionsConfig = field(default_factory=PermissionsConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)

    # ── paths ──────────────────────────────────────────────────────────────────

    @property
    def config_path(self) -> Path:
        return Path(self.profile_dir) / CONFIG_FILENAME

    @property
    def memory_dir(self) -> Path:
        return Path(self.profile_dir) / "memory"

    @property
    def model_dir(self) -> Path:
        return Path(self.profile_dir) / "models"

    # ── persistence ────────────────────────────────────────────────────────────

    def save(self) -> None:
        """Persist the configuration to *profile_dir/mcp.json*."""
        config_dir = Path(self.profile_dir)
        config_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "version": self.version,
            "profile_dir": self.profile_dir,
            "data_sources": asdict(self.data_sources),
            "permissions": asdict(self.permissions),
            "mcp": asdict(self.mcp),
        }
        with open(self.config_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")

    @classmethod
    def load(cls, profile_dir: str | None = None) -> GhostMCPConfig:
        """Load configuration from *profile_dir/mcp.json*.

        Raises ``FileNotFoundError`` when no config exists — callers should
        direct the user to run ``ghost-mcp init``.
        """
        resolved = profile_dir or str(DEFAULT_PROFILE_DIR)
        config_path = Path(resolved) / CONFIG_FILENAME
        if not config_path.exists():
            raise FileNotFoundError(
                f"No Ghost MCP config found at {config_path}. "
                "Run `ghost-mcp init` to set up."
            )
        with open(config_path, encoding="utf-8") as fh:
            data = json.load(fh)
        return cls._from_dict(data)

    @classmethod
    def exists(cls, profile_dir: str | None = None) -> bool:
        """Return ``True`` when a saved config is present on disk."""
        resolved = profile_dir or str(DEFAULT_PROFILE_DIR)
        return (Path(resolved) / CONFIG_FILENAME).exists()

    # ── private helpers ────────────────────────────────────────────────────────

    @classmethod
    def _from_dict(cls, data: dict) -> GhostMCPConfig:
        cfg = cls()
        cfg.version = data.get("version", VERSION)
        cfg.profile_dir = data.get("profile_dir", str(DEFAULT_PROFILE_DIR))

        ds = data.get("data_sources", {})
        cfg.data_sources = DataSourceConfig(
            local_files=ds.get("local_files", False),
            local_file_paths=ds.get("local_file_paths", []),
            browser_cache=ds.get("browser_cache", False),
            browser_cache_targets=ds.get("browser_cache_targets", []),
            email=ds.get("email", False),
            email_targets=ds.get("email_targets", []),
            calendar=ds.get("calendar", False),
            calendar_targets=ds.get("calendar_targets", []),
            custom_paths=ds.get("custom_paths", []),
        )

        perms = data.get("permissions", {})
        cfg.permissions = PermissionsConfig(
            read_only=perms.get("read_only", True),
            exclude_patterns=perms.get("exclude_patterns", list(DEFAULT_EXCLUDE_PATTERNS)),
        )

        mcp = data.get("mcp", {})
        cfg.mcp = MCPConfig(
            transport=mcp.get("transport", "stdio"),
            host=mcp.get("host", "localhost"),
            port=mcp.get("port", 8765),
        )
        return cfg
