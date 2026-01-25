# Task ID: 8

**Title:** Spotify Playlist Creation and Posting

**Status:** pending

**Dependencies:** 6

**Priority:** high

**Description:** Create Spotify playlist under configured account, add approved tracks in order, and post link to Discord channel.

**Details:**

Use spotipy with OAuth refresh token for authentication. Create playlist named 'Bluegrass Jam [MM/DD/YYYY]'. Add tracks in setlist order. Handle API errors gracefully, retry if needed, and notify admin if failure persists. Post playlist link to original Discord channel using discord.py. Store playlist info in setlists table. Ensure playlist-modify-public/private scopes are set.

**Test Strategy:**

Approve setlist and trigger playlist creation. Validate playlist name, track order, and link posting. Simulate Spotify API errors and verify error handling and admin notification.
