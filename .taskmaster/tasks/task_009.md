# Task ID: 9

**Title:** Song Version Memory and Setlist History Management

**Status:** pending

**Dependencies:** 8

**Priority:** medium

**Description:** Update song usage dates, maintain setlist-song relationships, and ensure version consistency across sessions.

**Details:**

On playlist creation, update last_used date for each song in songs table. Insert setlist and setlist_songs records to maintain history. Ensure first_used is set for new songs. Implement queries to retrieve version consistency stats. Use indices for efficient lookups. Log all updates for audit.

**Test Strategy:**

Create multiple setlists with repeat songs. Verify last_used and first_used dates update correctly. Check setlist-song relationships in database. Validate version consistency rate.
