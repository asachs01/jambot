# Admin Guide - Using the Approval Workflow

This guide explains how to use Jambot's admin approval workflow for validating song selections and creating Spotify playlists.

## Overview

As the designated admin, you'll receive Direct Messages (DMs) from Jambot whenever a setlist is detected. You'll review and approve song selections before the playlist is created.

## Workflow Steps

### 1. Setlist Detection

When the jam leader posts a setlist message, Jambot:
1. Detects and parses the message
2. Searches for each song on Spotify or checks the database
3. Sends you a DM with all song matches

### 2. Review Song Matches

You'll receive a DM with an embedded message for each song showing:

#### Pre-Approved Songs (✅)
Songs previously approved and stored in the database:

```
1. Will the Circle Be Unbroken
✅ Stored Version (Pre-approved)

Track: Will the Circle Be Unbroken
Artist: The Nitty Gritty Dirt Band
Album: Will the Circle Be Unbroken
[Spotify Link]
```

**What to do**:
- The stored version is automatically selected
- React with ✅ if you're happy with it
- To change it, you can search Spotify manually and reply with a different track link

#### Single Match Found (✅)
When Jambot finds exactly one match:

```
2. Blue Moon of Kentucky
✅ 1 match found - React to approve

Track: Blue Moon of Kentucky
Artist: Bill Monroe
Album: The Essential Bill Monroe
[Spotify Link]
```

**What to do**:
- React with ✅ to approve this version
- Or reply with a different Spotify track link if you prefer another version

#### Multiple Matches Found (1️⃣ 2️⃣ 3️⃣)
When Jambot finds multiple options:

```
3. Man of Constant Sorrow
🎵 3 matches found - React to select

1️⃣ Option 1
I Am a Man of Constant Sorrow
Stanley Brothers - The Complete Mercury Recordings
[Link]

2️⃣ Option 2
Man of Constant Sorrow
Soggy Bottom Boys - O Brother, Where Art Thou?
[Link]

3️⃣ Option 3
Man of Constant Sorrow
Norman Blake - Whiskey Before Breakfast
[Link]
```

**What to do**:
- React with 1️⃣, 2️⃣, or 3️⃣ to select your preferred version
- Or reply with a Spotify track link for a different version

#### No Match Found (❌)
When Jambot can't find the song:

```
4. Some Obscure Traditional Song
❌ No matches found
Reply with Spotify track link to add manually.
```

**What to do**:
- Search Spotify manually for the song
- Copy the track's Spotify link
- Reply to the DM with the link

### 3. Provide Manual Links

To manually add a song version, reply to the DM with a Spotify track link:

```
https://open.spotify.com/track/TRACK_ID_HERE
```

Jambot will:
- Validate the link
- Extract track information
- Confirm the selection
- Use this version for the playlist

### 4. Final Approval

After reviewing all songs, you'll receive a summary message:

```
✅ Review complete! React with ✅ to create the playlist or ❌ to cancel.
```

**What to do**:
- React with ✅ to create the Spotify playlist
- React with ❌ to cancel (no playlist will be created)

### 5. Playlist Creation

Once you approve:
1. Jambot creates a Spotify playlist named "Bluegrass Jam [DATE]"
2. Adds all approved tracks in setlist order
3. Posts the playlist link to the Discord channel
4. Stores the song versions in the database for future jams
5. Sends you a confirmation DM

## Manual Song Management

### Override a Song After Approval

Use this command in any channel where Jambot is present:

```
@jambot use this version of Will the Circle Be Unbroken for 11/18/2024 https://open.spotify.com/track/TRACK_ID
```

This will:
- Update the song in the pending setlist (before playlist creation)
- Store this version as the preferred version for future jams
- Confirm the change via DM

### Find a Spotify Track Link

1. Open Spotify (desktop, web, or mobile)
2. Find the song you want
3. Click the three dots (•••) next to the song
4. Select **"Share"** → **"Copy Song Link"**
5. Paste the link in your DM to Jambot

Example link format:
```
https://open.spotify.com/track/6rqhFgbbKwnb9MLmUQDhG6
```

## Best Practices

### Song Selection

1. **Consistency**: Use the same version of a song across jams when possible
   - Jambot remembers your choices
   - Pre-approved versions make future approvals faster

2. **Quality**: Choose official releases over covers when available
   - Check the artist and album names
   - Verify it's the right tempo/style for your jam

3. **Availability**: Ensure tracks are available in your region
   - Some tracks may be region-locked
   - Test the link before approving

### Handling Edge Cases

#### Song not on Spotify
- If a traditional song isn't available, pick the closest version
- Or skip it (don't react) and add it manually to the playlist later

#### Wrong song detected
- Reply with the correct Spotify link
- Jambot will use your manual selection

#### Multiple jams on same day
- Playlists are named by date, which could conflict
- Consider editing the playlist name in Spotify after creation
- Future enhancement: Support for multiple jams per day

## Privacy Settings

To receive DMs from Jambot:

1. Open Discord User Settings (gear icon)
2. Go to **Privacy & Safety**
3. Enable **"Allow direct messages from server members"**
4. Make sure you share a server with Jambot

## Troubleshooting

### Not receiving DMs

**Problem**: Jambot isn't sending you approval DMs

**Solutions**:
- Verify your User ID is correct in the bot's configuration
- Check your Discord privacy settings (see above)
- Ensure you share a server with Jambot
- Check if DMs from Jambot are being filtered or blocked

### Reactions not working

**Problem**: Your emoji reactions aren't being detected

**Solutions**:
- Make sure you're reacting to the correct message
- Wait a moment after the message appears before reacting
- Remove and re-add your reaction if it doesn't register
- Check bot logs for errors

### Wrong song version stored

**Problem**: The database has the wrong version of a song

**Solutions**:
- Use the manual override command:
  ```
  @jambot use this version of [song name] for [date] [spotify link]
  ```
- This updates both the current setlist and future defaults

### Playlist not created

**Problem**: You approved but the playlist wasn't created

**Solutions**:
- Check your DM for error messages from Jambot
- Verify Spotify credentials are valid
- Check bot logs for API errors
- Try again with a fresh setlist

### Can't find a song on Spotify

**Problem**: A song isn't available on Spotify

**Options**:
- Search for a cover version by another artist
- Search for a similar song by the original artist
- Skip the song (don't react) and add it manually later
- Contact the jam leader about substitutions

## Advanced Usage

### Batch Approvals

For familiar songs with stored versions:
1. Quickly react ✅ to all pre-approved songs
2. Focus your attention on new songs or multiple matches
3. Review the final summary before creating the playlist

### Custom Playlists

After creation, you can edit the Spotify playlist:
- Reorder songs
- Add/remove tracks
- Change playlist name
- Update description
- Make it collaborative

Changes in Spotify won't affect Jambot's database.

## Getting Help

If you encounter issues:

1. **Check the bot logs**:
   - Contact your system administrator
   - Logs show detailed error messages

2. **Review documentation**:
   - [Troubleshooting Guide](TROUBLESHOOTING.md)
   - [Setup Guides](README.md#documentation)

3. **Test the bot**:
   - Ask the jam leader to post a test setlist
   - Verify each step of the workflow

4. **Report issues**:
   - Note the date/time of the error
   - Save any error messages from DMs
   - Check if the issue is reproducible

## Workflow Example

Let's walk through a complete example:

### 1. Jam Leader Posts Setlist

```
Here's the upcoming setlist for the 7pm jam on November 18, 2024.
If you want to sing any of these, please let me know or comment below.

1. Will the Circle Be Unbroken (G)
2. Blue Moon of Kentucky (F)
3. Man of Constant Sorrow (A)
```

### 2. You Receive DM

Jambot sends you three messages:

**Message 1**: (Stored version)
```
1. Will the Circle Be Unbroken
✅ Stored Version (Pre-approved)
[Shows track details]
```
→ You react with ✅

**Message 2**: (Single match)
```
2. Blue Moon of Kentucky
✅ 1 match found
[Shows track details]
```
→ You react with ✅

**Message 3**: (Multiple matches)
```
3. Man of Constant Sorrow
🎵 3 matches found
[Shows 3 options]
```
→ You react with 2️⃣ (you prefer the Soggy Bottom Boys version)

### 3. Summary & Final Approval

```
✅ Review complete! React with ✅ to create the playlist or ❌ to cancel.
```
→ You react with ✅

### 4. Confirmation

Jambot sends:
```
✅ Playlist created successfully!
https://open.spotify.com/playlist/XXXXX
Posted to #jam-channel
```

And posts in the Discord channel:
```
🎵 Playlist created!
Bluegrass Jam November 18, 2024
[Spotify Link]
(3 songs)
```

Done! The playlist is ready for the jam.

## Tips for Efficiency

- Enable Discord notifications for Jambot DMs
- Keep Spotify open to preview tracks quickly
- Use keyboard shortcuts: `+` to add reaction, `ESC` to cancel
- Build a mental library of preferred versions
- Most songs will use stored versions after the first jam
