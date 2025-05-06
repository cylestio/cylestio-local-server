# Changelog

All notable changes to the cylestio-local-server package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.20] - 2025-05-06

### Fixed
- Fixed packaging to ensure `pip install cylestio-local-server` works properly
- Improved dynamic import system in src.py to work correctly in pip-installed packages
- Updated MANIFEST.in to ensure all required files are included in distribution
- Added proper package data configuration to pyproject.toml
- Added setup.py for compatibility with different installation methods

## [0.1.16] - 2025-05-06

### Added
- Improved handling of existing databases with clear messaging
- Added visual cues to indicate when a database is new vs. existing
- Fixed documentation URL to use the correct host and port

## [0.1.15] - 2025-05-06

### Fixed
- Fixed database path handling to correctly use custom database paths
- Resolved issue where database URL was hardcoded instead of using user-provided path
- Updated documentation URL to use the correct port number

## [0.1.14] - 2025-05-06

### Added
- Added automatic database initialization during server startup
- Server now creates missing tables if they don't exist
- Better error handling for database initialization failures

## [0.1.13] - 2025-05-06

### Fixed
- Added package import compatibility for both development and production environments
- Created src bridge module to allow correct imports when installed via PyPI
- Proper package structure to ensure correct module importing

## [0.1.12] - 2025-05-06

### Fixed
- Fixed test errors by adding missing test dependencies
- Added httpx and other required packages to development dependencies
- Fixed SQLAlchemy "Table already exists" errors with extend_existing=True
- Removed duplicate test files that were causing import errors

## [0.1.11] - 2025-05-05

### Added
- Initial public release on PyPI
- Basic server functionality with API endpoints
- Database models for telemetry data
- Command-line interface for starting the server 