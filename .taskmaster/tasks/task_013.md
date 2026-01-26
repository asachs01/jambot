# Task ID: 13

**Title:** Fix Bug: Persist Manual DM Song Submissions to Database Immediately

**Status:** done

**Dependencies:** 4, 5 ⧖

**Priority:** high

**Description:** Fix the bug where songs submitted via manual DM reply to song suggestion embeds are only stored in memory but not persisted to the database until playlist creation, causing data loss if the approval workflow doesn't complete.

**Details:**

ROOT CAUSE: In src/bot.py, the handle_dm_message() function (line 155) allows users to reply to song suggestion embeds with Spotify URLs. When they do, it updates workflow['selections'][song_number] in memory (line 232) and sends a confirmation message (lines 240-245), but never calls db.add_or_update_song() to persist the song to the database. Songs are only stored when create_playlist_from_workflow() runs (triggered by ✅ reaction on summary message).

IMPLEMENTATION STEPS:
1. Locate the handle_dm_message() function in src/bot.py around line 155
2. After the line that updates workflow['selections'][song_number] (line 232), add a call to persist the song immediately
3. Extract the guild_id from the workflow dictionary (workflow['guild_id'])
4. Call self.db.add_or_update_song() with the following parameters:
   - guild_id: from workflow dict
   - song_title: the song name from the workflow
   - spotify_track_id: extracted from the Spotify URL
   - spotify_url: the URL provided by the user
   - artist: extract from Spotify track info
   - album: extract from Spotify track info
5. Add logging statement: logger.info(f"Stored manual song submission for '{song_title}' via DM reply to database")
6. Wrap the database call in try/except to handle any database errors gracefully and notify the user if storage fails
7. Ensure the confirmation message (lines 240-245) still sends to the user after successful storage
8. The song will still be linked to the setlist later when approval completes (existing behavior in create_playlist_from_workflow)

EXAMPLE CODE LOCATION:
- Reference src/bot.py lines 713-721 for how songs ARE properly stored in create_playlist_from_workflow()
- Use the same db.add_or_update_song() method pattern from src/database.py line 159

ERROR HANDLING:
- If database storage fails, log the error and notify the user that their submission was received but may need to be resubmitted
- Ensure workflow selections are still updated even if database storage fails (graceful degradation)

**Test Strategy:**

1. MANUAL SONG SUBMISSION TEST:
   - Trigger setlist detection workflow with songs that need manual selection
   - Reply to a song suggestion embed via DM with a valid Spotify URL
   - Verify confirmation message is sent to the user
   - Query the songs table directly and confirm the song was stored with correct spotify_track_id, spotify_url, artist, and album
   - Check logs for "Stored manual song submission" message

2. WORKFLOW COMPLETION TEST:
   - After manual song submission, complete the approval workflow by adding ✅ reaction
   - Verify playlist is created successfully
   - Confirm the manually submitted song appears in the playlist
   - Check that setlist_songs table contains the link between the song and setlist

3. INCOMPLETE WORKFLOW TEST:
   - Submit a song manually via DM reply
   - Do NOT complete the approval workflow (don't add ✅ reaction)
   - Query the songs table and verify the song is still stored
   - Restart the bot and verify the song remains in the database

4. DATABASE ERROR HANDLING TEST:
   - Simulate a database error (temporarily make database read-only or disconnect)
   - Submit a song via DM reply
   - Verify user receives appropriate error notification
   - Confirm workflow selections are still updated in memory
   - Restore database and verify subsequent submissions work correctly

5. LOGGING VERIFICATION:
   - Review logs after manual song submission
   - Confirm log entry includes song title, guild_id, and success/failure status
   - Verify log level is appropriate (INFO for success, ERROR for failures)
