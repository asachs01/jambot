---
title: Changelog
description: All notable changes to JamBot
---

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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

### Fixed
- Fix crash when creating playlist with missing selections when DISCORD_ADMIN_ID env var is not set
- Improve error message for missing song selections to explain how to retry after selecting songs
- Switch to raw reaction events for more reliable DM reaction handling
- Fix workflow cleanup bug: workflows now remain active when missing songs detected
- Fix manual song submissions: songs submitted via DM reply or emoji reaction are now persisted immediately
- Persist active approval workflows to database so they survive bot restarts
- Fix Spotify API errors in headless environments by using access token directly
- Fix selection key mismatch: use string keys consistently for JSONB compatibility

## [1.0.0] - 2025-12-16

### Added
- Support building DATABASE_URL from PG* environment variables
- `/jambot-status` command to view current configuration
- `/jambot-process` command for manual setlist processing
- Multi-guild Spotify authentication support
- PostgreSQL database support

### Changed
- Migrated database from SQLite to PostgreSQL

### Fixed
- Check spotify_tokens table for authorization status
- Ensure manual process command sender receives DM workflow
- Allow admins to use `/jambot-process`, improve error message
- Allow notes after song key in setlist parser

## [0.9.0] - 2025-11-01

### Added
- Modal-based configuration via `/jambot-setup`
- Per-server Spotify credentials
- Multiple jam leaders and approvers per server
- `/jambot-getid` command for getting user IDs
- `/jambot-settings` for advanced configuration
- Song version memory across jams

### Changed
- Configuration now stored in database per-server
- Approval workflow sent to all configured approvers

## [0.8.0] - 2025-10-15

### Added
- Docker deployment support
- DigitalOcean App Platform deployment
- Health check endpoint
- Automatic bot restart on failures

### Fixed
- Database persistence in containers
- Memory usage optimization

## [0.7.0] - 2025-10-01

### Added
- Initial release
- Discord bot for setlist detection
- Spotify integration for song search
- Admin approval workflow via DM
- Automatic playlist creation
- SQLite database for song storage
