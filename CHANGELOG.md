# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Fix crash when creating playlist with missing selections when DISCORD_ADMIN_ID env var is not set. Now uses database approvers instead.
- Improve error message for missing song selections to explain how to retry after selecting songs.

## [1.0.0] - 2025-12-16

### Added
- Support building DATABASE_URL from PG* environment variables
- /jambot-status command to view current configuration
- /jambot-process command for manual setlist processing
- Multi-guild Spotify authentication support
- PostgreSQL database support

### Changed
- Migrated database from SQLite to PostgreSQL

### Fixed
- Check spotify_tokens table for authorization status
- Ensure manual process command sender receives DM workflow
- Allow admins to use /jambot-process, improve error message
- Allow notes after song key in setlist parser
