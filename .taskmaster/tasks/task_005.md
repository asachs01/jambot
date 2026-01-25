# Task ID: 5

**Title:** Song Matching: Database Lookup and Spotify Search

**Status:** in-progress

**Dependencies:** 3, 4

**Priority:** high

**Description:** For each song, check for previously approved versions in the database, otherwise search Spotify for matches.

**Details:**

For each song, query the songs table for existing version. If not found, use spotipy v2.23+ to search Spotify with exact title. If no match, try common bluegrass variations (maintain a mapping or use a configurable list). Limit fuzzy matching to avoid irrelevant results. Return up to 3 matches per new song, capturing track name, artist, album, Spotify track ID, and URL. Handle Spotify API rate limits with exponential backoff and retries.

**Test Strategy:**

Test with songs present and absent in the database. Validate Spotify search results for accuracy and relevance. Simulate rate limits and verify retry logic.
