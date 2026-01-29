# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **BREAKING**: Chord chart PDF generation, transposition, and rendering now use Premium API instead of local code
- Manual chart creation via modal now uses Premium API for PDF rendering
- Chart view command now uses Premium API for PDF rendering and transposition
- Transpose command now uses Premium API for both transposition and PDF rendering
- Mention handler now uses Premium API for chart lookup, transposition, and PDF rendering
- Added graceful degradation when Premium API is unavailable (charts saved but PDF preview may be unavailable)

### Added
- New `render_pdf()` method in PremiumClient for rendering chart data to PDF
- New `transpose_chart()` method in PremiumClient for transposing charts
- New `create_manual_chart()` method in PremiumClient for manual chart creation
- New `TransposedChart` dataclass for transposition results
- Local helper functions for parsing modal input and converting database format to API format
- Chord chart generation feature with `/jambot-chart` slash command (create, view, list, transpose).
- PDF chord charts in TNBGJ songbook format (landscape letter, lyrics left, chord grid right).
- Chromatic transposition utility with bluegrass-appropriate sharp/flat spellings.
- Mention-based chord chart requests (`@jambot chord chart for Mountain Dew in G`).
- `chord_charts` PostgreSQL table for storing chord progressions per guild.
- Health check now monitors Discord connection status - returns 503 when disconnected to trigger automatic restart
- `/jambot-feedback` command for users to submit bug reports, feature requests, and general feedback
- Feedback notifications sent to maintainer via DM (configure with `FEEDBACK_NOTIFY_USER_ID`)
- Post-playlist satisfaction ratings with thumbs up/down reactions
- Usage analytics tracking for playlists created, commands used, and feedback submitted
- New database tables: `feedback` for user feedback, `usage_stats` for aggregated analytics
- `/jambot-retry` command to retry playlist creation after fixing missing song selections
- `/jambot-workflow-status` command to view active approval workflows and their progress
- `/jambot-cancel-workflow` command to explicitly cancel an active workflow
- Workflow expiration: workflows automatically expire after 48 hours and are cleaned up every 6 hours
- Improved error messages for missing song selections with workflow ID and clear instructions
- Astro Starlight documentation site at jambot.app with bluegrass branding
- GitHub Actions workflow for automatic documentation deployment

### Fixed
- Fix crash when creating playlist with missing selections when DISCORD_ADMIN_ID env var is not set. Now uses database approvers instead.
- Improve error message for missing song selections to explain how to retry after selecting songs.
- Switch to raw reaction events for more reliable DM reaction handling.
- Fix workflow cleanup bug: workflows now remain active when missing songs detected, allowing users to fix and retry with checkmark
- Fix manual song submissions: songs submitted via DM reply or emoji reaction are now persisted to database immediately
- Persist active approval workflows to database so they survive bot restarts
- Fix Spotify API errors in headless environments by using access token directly instead of auth_manager
- Fix selection key mismatch: use string keys consistently for JSONB compatibility (fixes "missing songs" false positives after restart)

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
