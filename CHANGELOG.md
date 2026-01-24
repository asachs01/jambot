# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Chord chart generation feature with `/jambot-chart` slash command (create, view, list, transpose).
- PDF chord charts in TNBGJ songbook format (landscape letter, lyrics left, chord grid right).
- Chromatic transposition utility with bluegrass-appropriate sharp/flat spellings.
- Mention-based chord chart requests (`@jambot chord chart for Mountain Dew in G`).
- `chord_charts` PostgreSQL table for storing chord progressions per guild.
- Persist approval workflows to database so they survive bot restarts.

### Fixed
- Fix crash when creating playlist with missing selections when DISCORD_ADMIN_ID env var is not set. Now uses database approvers instead.
- Improve error message for missing song selections to explain how to retry after selecting songs.
- Switch to raw reaction events for more reliable DM reaction handling.

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
