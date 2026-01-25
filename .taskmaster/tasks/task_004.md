# Task ID: 4

**Title:** SQLite Database Schema Design and Implementation

**Status:** pending

**Dependencies:** 1

**Priority:** high

**Description:** Design and implement the SQLite database schema for songs, setlists, and setlist-song relationships.

**Details:**

Create tables: songs, setlists, setlist_songs as specified. Use sqlite3 with connection pooling for reliability. Ensure atomic transactions for all write operations. Implement schema migrations using Alembic or a simple versioning script. Set up indices on song_title and setlist date for fast lookups. Use parameterized queries to prevent SQL injection.

**Test Strategy:**

Run schema creation and migration scripts. Validate table structure and constraints. Test atomicity by simulating concurrent writes. Verify indices improve query performance.
