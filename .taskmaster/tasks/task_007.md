# Task ID: 7

**Title:** Manual Song Management Command Implementation

**Status:** pending

**Dependencies:** 4, 6

**Priority:** medium

**Description:** Implement the '@jambot use this version of [song name] for [setlist date] [spotify link]' command for manual overrides.

**Details:**

Parse command using discord.py command framework. Validate Spotify link format using regex. Update song version in setlist (if before playlist creation) and in songs table for future use. Confirm update to admin via DM. Log all manual overrides for audit. Ensure command is only accessible to admin.

**Test Strategy:**

Test command with valid and invalid Spotify links. Verify updates in database and setlist. Confirm admin receives confirmation. Check access control.
