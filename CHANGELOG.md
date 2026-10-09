# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- pytest suite (tests/) covering the tool registry, CLI fallback and the stdio server
- CI workflow running tests and the smoke check on pushes to main and on pull requests
- Dependabot for pip and GitHub Actions
- uv.lock, .gitignore and SECURITY.md

### Fixed

- ghostchimera dependency now accepts the published 0.4.0b0 pre-release (install was unsatisfiable)
- mcp capped below 2.0, whose API removed the server decorators this package uses
- CLI-backed tools return a clear error instead of crashing when the ghostchimera CLI is missing or times out
