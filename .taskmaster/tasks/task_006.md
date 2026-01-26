# Task ID: 6

**Title:** Admin Validation Workflow via Discord DM

**Status:** pending

**Dependencies:** 5 ⧖

**Priority:** high

**Description:** Send a DM to the admin with song match details, support emoji-based approval, manual overrides, and summary confirmation.

**Details:**

Use discord.py to send formatted DMs to DISCORD_ADMIN_ID. For each song, display: pre-approved version (✅), single match (✅), multiple matches (1️⃣ 2️⃣ 3️⃣), or no match (❌, prompt for link). Listen for emoji reactions and message replies. Allow admin to override with Spotify link. After all songs, present summary and request final approval. Implement async/await for all Discord operations. Log all admin actions for audit.

**Test Strategy:**

Simulate setlist detection and verify DM formatting. Test all approval scenarios (emoji, manual link, skip). Confirm summary and final approval flow. Validate logging of admin actions.
