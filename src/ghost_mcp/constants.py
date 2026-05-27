"""Shared constants for Ghost MCP."""

from __future__ import annotations

from pathlib import Path

VERSION = "0.1.0"

DEFAULT_PROFILE_DIR: Path = Path.home() / ".ghost"
CONFIG_FILENAME = "mcp.json"

# ── Data source catalogues ─────────────────────────────────────────────────────

BROWSER_TARGETS: dict[str, str] = {
    "chrome": "Google Chrome",
    "firefox": "Mozilla Firefox",
    "safari": "Apple Safari",
    "edge": "Microsoft Edge",
    "brave": "Brave Browser",
}

EMAIL_TARGETS: dict[str, str] = {
    "apple_mail": "Apple Mail",
    "thunderbird": "Mozilla Thunderbird",
    "gmail_imap": "Gmail (IMAP)",
    "outlook": "Microsoft Outlook",
}

CALENDAR_TARGETS: dict[str, str] = {
    "apple_calendar": "Apple Calendar",
    "google_calendar": "Google Calendar",
    "outlook_calendar": "Outlook Calendar",
}

# Sensitive patterns always skipped by the ghost scanner
DEFAULT_EXCLUDE_PATTERNS: tuple[str, ...] = (
    ".env",
    ".env.*",
    "*.key",
    "*.pem",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_rsa.pub",
    "id_ed25519",
    "id_ed25519.pub",
    "*.secret",
    "*.credentials",
    ".ssh",
    "node_modules",
    ".git",
    "__pycache__",
    "*.pyc",
)
