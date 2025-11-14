# Product Requirements Document: Bluegrass Jam Setlist to Spotify Playlist Bot

## 1. Product Overview

### 1.1 Purpose
Create a Discord bot that automatically converts bluegrass jam setlist messages into Spotify playlists, with an admin approval workflow and memory of preferred song versions across multiple jam sessions.

### 1.2 Target Users
- Primary: Bluegrass jam group organizers and administrators
- Secondary: Jam session participants who want to preview upcoming setlists

### 1.3 Success Metrics
- Bot successfully detects and processes 95%+ of posted setlists
- Admin approval workflow completion time < 5 minutes
- Song version consistency rate of 90%+ across repeat songs
- Zero manual playlist creation needed

## 2. User Stories

### 2.1 Core User Stories
1. **As a jam leader**, I want to post my setlist in Discord and have it automatically converted to a Spotify playlist, so participants can familiarize themselves with the songs.

2. **As an admin**, I want to review and approve song matches before the playlist is created, so I can ensure quality and accuracy.

3. **As an admin**, I want the bot to remember which versions of songs we've used before, so we maintain consistency across jam sessions.

4. **As an admin**, I want to manually override song selections when needed, so I have full control over the final playlist.

### 2.2 Secondary User Stories
5. **As a participant**, I want to see the Spotify playlist link posted in the channel, so I can easily access it.

6. **As an admin**, I want to update song versions after playlist creation, so future setlists use the correct versions.

## 3. Functional Requirements

### 3.1 Setlist Detection
**FR-1.1** The bot MUST monitor messages from a configurable Discord user (jam leader)

**FR-1.2** The bot MUST detect messages matching this pattern:
```
Here's the upcoming setlist for the [TIME] jam on [DATE]. [Optional text]

1. Song Name (Key)
2. Song Name (Key)
...
```

**FR-1.3** The bot MUST extract:
- Date of jam session
- Time of jam session  
- List of song titles (without key information)

**FR-1.4** The bot SHOULD allow minor variations in the intro text format

### 3.2 Song Matching

**FR-2.1** The bot MUST check the SQLite database first for previously approved versions of each song

**FR-2.2** For new songs, the bot MUST search Spotify using the exact extracted title first

**FR-2.3** If no exact matches found, the bot MUST try common bluegrass variations:
- Example: "Will the Circle" → "Will the Circle Be Unbroken"

**FR-2.4** The bot MUST NOT use overly fuzzy matching that returns irrelevant results

**FR-2.5** The bot MUST return up to 3 matching tracks per song for new songs

**FR-2.6** The bot MUST capture for each match:
- Track name
- Artist name
- Album name
- Spotify track ID
- Spotify track URL

### 3.3 Admin Validation Workflow

**FR-3.1** The bot MUST send a DM to the configured admin user when a setlist is detected

**FR-3.2** For each song, the bot MUST present:
- **Previously approved songs**: Display stored version with ✅ reaction (pre-approved but changeable)
- **New songs with 1 match**: Display track details with ✅ reaction to confirm
- **New songs with multiple matches**: Display top 3 results with 1️⃣ 2️⃣ 3️⃣ reactions
- **No matches found**: Display "❌ No matches found - reply with Spotify link"

**FR-3.3** Track display MUST include:
- Track name
- Artist name
- Album name
- Clickable Spotify link

**FR-3.4** Admin approval options MUST include:
- React with emoji to approve/select (✅ 1️⃣ 2️⃣ 3️⃣)
- Reply with Spotify track link for manual specification
- No reaction (skip song, handle manually later)

**FR-3.5** After all songs processed, the bot MUST show a summary and request final approval to create playlist

**FR-3.6** The bot MUST wait for final approval before creating the Spotify playlist

### 3.4 Manual Song Management

**FR-4.1** The bot MUST support a command: `@jambot use this version of [song name] for [setlist date] [spotify link]`

**FR-4.2** This command MUST:
- Update the song in the approved setlist (if before playlist creation)
- Update the stored version in the database for future use
- Confirm the update to the admin

**FR-4.3** The bot MUST validate that the provided link is a valid Spotify track URL

### 3.5 Song Version Memory

**FR-5.1** The bot MUST store approved song versions in a SQLite database

**FR-5.2** Database schema MUST include:

**songs table:**
- id (PRIMARY KEY)
- song_title (UNIQUE)
- spotify_track_id
- spotify_track_name
- artist
- album
- spotify_url
- first_used (DATE)
- last_used (DATE)

**setlists table:**
- id (PRIMARY KEY)
- date
- time
- playlist_name
- spotify_playlist_id
- spotify_playlist_url
- created_at (TIMESTAMP)

**setlist_songs table:**
- id (PRIMARY KEY)
- setlist_id (FOREIGN KEY)
- song_id (FOREIGN KEY)
- position

**FR-5.3** The bot MUST update `last_used` date when a song is used in a new setlist

**FR-5.4** The bot MUST store complete setlist history with song-to-setlist relationships

### 3.6 Spotify Playlist Creation

**FR-6.1** The bot MUST create playlists under the configured Spotify account

**FR-6.2** Playlist naming MUST follow: "Bluegrass Jam [MM/DD/YYYY]" (e.g., "Bluegrass Jam 11/18/2024")

**FR-6.3** The bot MUST add approved tracks to the playlist in setlist order

**FR-6.4** The bot MUST post the playlist link to the original Discord channel where the setlist was posted

**FR-6.5** The bot MUST store playlist information in the database

**FR-6.6** The bot MUST handle Spotify API errors gracefully and notify admin

## 4. Non-Functional Requirements

### 4.1 Performance
**NFR-1.1** Setlist detection MUST occur within 5 seconds of message posting

**NFR-1.2** Spotify search results MUST be returned within 10 seconds per song

**NFR-1.3** Playlist creation MUST complete within 30 seconds of final approval

### 4.2 Reliability
**NFR-2.1** The bot MUST have 99% uptime during active hours (configurable)

**NFR-2.2** Database operations MUST be atomic to prevent data corruption

**NFR-2.3** The bot MUST log all errors with sufficient detail for debugging

**NFR-2.4** The bot MUST gracefully handle Discord and Spotify API rate limits

### 4.3 Security
**NFR-3.1** All API credentials MUST be stored in environment variables, not hardcoded

**NFR-3.2** The bot MUST use OAuth refresh tokens for Spotify authentication

**NFR-3.3** Database file MUST have appropriate file permissions (read/write for bot only)

### 4.4 Maintainability
**NFR-4.1** Code MUST use async/await patterns for Discord operations

**NFR-4.2** Code MUST include comprehensive error handling and logging

**NFR-4.3** Code MUST be well-commented with clear function documentation

**NFR-4.4** Configuration MUST be externalized in .env file

## 5. Technical Specifications

### 5.1 Technology Stack
- **Language**: Python 3.11+
- **Discord Library**: discord.py
- **Spotify Library**: spotipy
- **Database**: SQLite
- **Containerization**: Docker
- **Deployment**: DigitalOcean Container App

### 5.2 Configuration

Environment variables required:
```
DISCORD_BOT_TOKEN=<token>
DISCORD_JAM_LEADER_ID=<user_id>
DISCORD_ADMIN_ID=<user_id>
SPOTIFY_CLIENT_ID=<client_id>
SPOTIFY_CLIENT_SECRET=<client_secret>
SPOTIFY_REDIRECT_URI=<redirect_uri>
SPOTIFY_REFRESH_TOKEN=<refresh_token>
```

### 5.3 Deployment Architecture

**Container Requirements:**
- Single container running the bot process
- Persistent volume mount for SQLite database
- Environment variables configured in DO Container App
- Automatic restart on failure

**Resource Requirements:**
- Memory: 512MB minimum
- CPU: 0.5 vCPU minimum
- Storage: 1GB persistent volume for database

### 5.4 External Integrations

**Discord API:**
- Required Intents: Message Content, Server Members (optional)
- Required Permissions: Send Messages, Read Messages/View Channels, Add Reactions, Send Messages in Threads

**Spotify API:**
- Required Scopes: playlist-modify-public, playlist-modify-private
- Authentication: OAuth 2.0 with refresh token

## 6. Setup and Onboarding

### 6.1 Discord Bot Setup Process
1. Create application in Discord Developer Portal
2. Create bot and enable required intents
3. Generate bot token
4. Configure OAuth2 URL with required permissions
5. Add bot to server
6. Obtain user IDs for jam leader and admin

### 6.2 Spotify API Setup Process
1. Create app in Spotify Developer Dashboard
2. Obtain Client ID and Client Secret
3. Configure redirect URI
4. Run OAuth flow to obtain refresh token
5. Add credentials to environment variables

### 6.3 Deployment Process
1. Build Docker image
2. Push to DigitalOcean Container Registry
3. Create Container App in DO
4. Configure environment variables
5. Attach persistent volume
6. Deploy and verify

## 7. Error Handling

### 7.1 Error Scenarios

**E-1** Setlist message format not recognized
- Action: Log warning, do not process
- Admin notification: None (reduce noise)

**E-2** Spotify API returns no matches for a song
- Action: Present "No matches found" in validation DM
- Admin notification: In validation workflow

**E-3** Spotify API rate limit exceeded
- Action: Retry with exponential backoff
- Admin notification: If retries exhausted

**E-4** Database operation fails
- Action: Log error, retry once
- Admin notification: DM admin if retry fails

**E-5** Playlist creation fails
- Action: Save approved setlist to database
- Admin notification: DM admin with error details and option to retry

**E-6** Discord API error
- Action: Log error, retry with backoff
- Admin notification: If critical operation fails

### 7.2 Logging Requirements
- Log level: INFO for normal operations, ERROR for failures
- Log destination: Console (stdout) and rotating file
- Log format: Timestamp, level, module, message
- Log retention: 7 days

## 8. Future Enhancements (Out of Scope for v1)

**FE-1** Command to list all stored song versions: `@jambot list songs`

**FE-2** Command to view past setlists: `@jambot show setlist [date]`

**FE-3** Ability to regenerate playlist from past setlist

**FE-4** Statistics dashboard: most played songs, frequency analysis

**FE-5** Multi-server support with separate databases

**FE-6** Web interface for song version management

**FE-7** Automatic notification to participants when playlist is ready

**FE-8** Support for alternative streaming services (Apple Music, YouTube Music)

## 9. Acceptance Criteria

### 9.1 Definition of Done
- [ ] Bot successfully detects setlist messages from configured user
- [ ] Bot extracts date, time, and song list accurately
- [ ] Bot searches Spotify and returns relevant matches
- [ ] Bot checks database for previously approved versions
- [ ] Bot sends validation DM with proper formatting
- [ ] Bot responds to emoji reactions correctly
- [ ] Bot accepts manual Spotify links as overrides
- [ ] Bot creates Spotify playlist with correct naming
- [ ] Bot posts playlist link to original channel
- [ ] Bot stores all data in SQLite database
- [ ] Manual override command works correctly
- [ ] All errors are logged appropriately
- [ ] Setup documentation is complete and accurate
- [ ] Dockerfile builds successfully
- [ ] Container deploys to DigitalOcean successfully
- [ ] Database persists across container restarts

### 9.2 Test Scenarios

**Test 1: Basic Setlist Processing**
- Input: Standard setlist message from jam leader
- Expected: Bot detects, extracts songs, sends validation DM

**Test 2: Song Memory**
- Input: Setlist with previously used songs
- Expected: Bot shows stored versions, marks as pre-approved

**Test 3: Multiple Matches**
- Input: Song with 3+ Spotify matches
- Expected: Bot shows top 3 with emoji reactions

**Test 4: No Matches**
- Input: Obscure song with no Spotify results
- Expected: Bot shows "No matches found", accepts manual link

**Test 5: Manual Override**
- Input: `@jambot use this version of Will the Circle for 11/18/2024 [link]`
- Expected: Bot updates setlist and database

**Test 6: Playlist Creation**
- Input: Admin approves all songs and confirms
- Expected: Playlist created with correct name, songs in order, link posted

**Test 7: Error Recovery**
- Input: Spotify API temporarily unavailable
- Expected: Bot retries, notifies admin if all retries fail

**Test 8: Container Restart**
- Input: Container restarts
- Expected: Database intact, bot resumes normal operation

## 10. Documentation Requirements

**D-1** README with setup instructions for Discord and Spotify

**D-2** .env.example file with all required variables

**D-3** Database schema documentation

**D-4** Deployment guide for DigitalOcean Container App

**D-5** Admin user guide for approval workflow

**D-6** Troubleshooting guide for common issues

## 11. Constraints and Assumptions

### 11.1 Constraints
- Spotify free tier rate limits apply
- Discord bot must be in the server to monitor messages
- SQLite database size practical limit ~1GB
- DigitalOcean Container App pricing applies

### 11.2 Assumptions
- Jam leader posts setlists in consistent format
- Admin responds to validation DMs within reasonable time
- Bluegrass songs are generally available on Spotify
- Container has reliable internet connectivity
- Database volume has sufficient space

## 12. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Spotify API changes | High | Low | Use stable API version, monitor deprecations |
| Discord API changes | High | Low | Use maintained discord.py library, monitor updates |
| Database corruption | Medium | Low | Regular backups, atomic transactions |
| Rate limiting | Medium | Medium | Implement backoff, cache results where possible |
| Song matching accuracy | Medium | Medium | Admin validation workflow catches errors |
| Container storage full | Low | Low | Monitor disk usage, implement log rotation |

---

**Document Version**: 1.0  
**Last Updated**: November 14, 2025  
**Author**: Aaron Sachs  
**Status**: Ready for Development
