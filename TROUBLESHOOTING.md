# Troubleshooting Guide

This guide covers common issues with Jambot and their solutions.

## Table of Contents

- [🔍 Quick Diagnosis: Bot Not Detecting Messages](#-quick-diagnosis-bot-not-detecting-messages)
- [Bot Status Issues](#bot-status-issues)
- [Discord Integration](#discord-integration)
- [Spotify Integration](#spotify-integration)
- [Database Issues](#database-issues)
- [Deployment Issues](#deployment-issues)
- [Performance Issues](#performance-issues)
- [Common Error Messages](#common-error-messages)

---

## 🔍 Quick Diagnosis: Bot Not Detecting Messages

If your bot is **online** but **not responding** to messages, work through these steps in order:

### Step 1: Verify Message Content Intent (MOST COMMON ISSUE)

**This is the #1 reason bots don't detect messages.**

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your Jambot application
3. Click **"Bot"** in the left sidebar
4. Scroll down to **"Privileged Gateway Intents"**
5. Ensure **"Message Content Intent"** is toggled **ON** (should be blue)
6. If you made a change, click **"Save Changes"**
7. **Restart your bot**:
   ```bash
   docker compose down
   docker compose up -d
   ```

**Important**: Even though the intent is enabled in the code (`intents.message_content = True`), it MUST also be enabled in the Developer Portal.

### Step 2: Verify Your User ID

The bot is configured to only respond to specific jam leader user IDs.

**To check your actual user ID**:
1. Enable Developer Mode in Discord: Settings → Advanced → Developer Mode ON
2. Right-click your username anywhere
3. Click "Copy User ID"
4. Note your user ID (it will be a long number like `123456789012345678`)

**If the bot isn't responding**:
- You may not be configured as a jam leader
- Use `/jambot-setup` to add yourself as a jam leader
- Or check that the `.env` file has the correct `DISCORD_JAM_LEADER_ID`

### Step 3: Verify Bot Can See the Channel

1. Look at the member list on the right side of the channel
2. Find **jambot** in the list
3. If the bot isn't there:
   - Right-click the channel → Edit Channel → Permissions
   - Add jambot
   - Enable "View Channel" permission

### Step 4: Test Message Format

Use this exact test message (you can modify the date/time):

```
Here's the setlist for the 7pm jam on November 20th.

1. Will the Circle Be Unbroken
2. Rocky Top
3. Man of Constant Sorrow
```

**Critical Requirements**:
- Line 1 must contain: `here's the setlist for the [TIME] jam on [DATE].`
- There must be a **period (.)** after the date
- Songs must be numbered: `1. Song Title`
- Post from a jam leader account (configured via `/jambot-setup` or `.env`)

### Step 5: Check the Logs

Watch the logs in real-time:

```bash
docker compose logs -f
```

**If working correctly, you should see**:
```
jambot | INFO - Received message from <your name> (ID: YOUR_USER_ID)
jambot | INFO - Message content preview: Here's the setlist for the 7pm jam...
jambot | INFO - Detected setlist message from jam leader in channel 123456789
```

**Diagnosis based on what you see**:

| What You See | Problem | Solution |
|-------------|---------|----------|
| No "Received message" logs at all | Message Content Intent not enabled | Go back to Step 1 |
| Bot can't see the channel | Go back to Step 3 |
| "Received message" but wrong user ID | Not configured as jam leader | Use `/jambot-setup` to add yourself |
| "Received message" with correct ID but no "Detected setlist" | Message format wrong | Check message against Step 4 requirements |
| "Detected setlist message" | ✅ Working! | Bot should now send you a DM |

### Step 6: If Still Not Working

**Check the Discord Developer Portal settings again**:
1. Ensure these permissions are enabled for the bot:
   - Send Messages
   - Read Messages/View Channels
   - Add Reactions
   - Read Message History

2. Verify the bot has these intents:
   - Message Content Intent ← **MOST IMPORTANT**
   - Server Members Intent
   - Message Intent (auto-enabled)

**Restart after any changes**:
```bash
docker compose down && docker compose up -d
```

---

## Bot Status Issues

### Bot shows as offline

**Symptoms**: Bot appears offline in Discord server

**Possible Causes**:
1. Bot process isn't running
2. Invalid Discord token
3. Network connectivity issues

**Solutions**:

```bash
# Check if bot is running (local deployment)
ps aux | grep python | grep jambot

# Check logs for errors
tail -f logs/jambot.log

# Verify token in .env
cat .env | grep DISCORD_BOT_TOKEN

# Test network connectivity
ping discord.com

# Restart the bot
docker-compose restart  # or python -m src.main
```

### Bot connects then immediately disconnects

**Symptoms**: Bot appears online briefly, then goes offline

**Possible Causes**:
1. Missing required intents
2. Configuration validation error
3. Database initialization failure

**Solutions**:

1. Check Discord Developer Portal:
   - Go to your app → Bot section
   - Verify **Message Content Intent** is enabled
   - Save changes and restart bot

2. Check logs for configuration errors:
```bash
grep "Configuration error" logs/jambot.log
grep "Missing required" logs/jambot.log
```

3. Verify all environment variables are set:
```bash
python -c "from src.config import Config; Config.validate()"
```

---

## Discord Integration

### Bot doesn't detect setlist messages

**Symptoms**: Jam leader posts setlist, but bot doesn't respond

**Possible Causes**:
1. Wrong jam leader User ID configured
2. Bot can't read messages in channel
3. Setlist format doesn't match pattern

**Solutions**:

1. Verify jam leader ID:
```bash
# Check configured ID
grep DISCORD_JAM_LEADER_ID .env

# Get actual ID: Enable Developer Mode in Discord, right-click user, Copy User ID
```

2. Check bot permissions:
   - Bot needs **Read Messages/View Channels** permission
   - Verify bot role has access to the channel

3. Test setlist format:
   - Must contain: "setlist for the [TIME] jam on [DATE]"
   - Songs must be numbered: "1. Song Name (Key)"
   - Check logs for parsing errors:
```bash
grep "setlist" logs/jambot.log -i
```

### Bot can't send DMs to admin

**Symptoms**: Admin doesn't receive approval workflow DMs

**Possible Causes**:
1. Wrong admin User ID configured
2. Admin has DMs disabled
3. Bot and admin don't share a server

**Solutions**:

1. Verify admin ID:
```bash
grep DISCORD_ADMIN_ID .env
```

2. Check admin's privacy settings:
   - Discord → User Settings → Privacy & Safety
   - Enable "Allow direct messages from server members"

3. Ensure bot and admin share a server:
   - Bot must be in at least one server with the admin user

4. Test DM functionality:
```python
# Add test code to bot.py temporarily
async def test_dm():
    admin = await self.fetch_user(int(Config.DISCORD_ADMIN_ID))
    dm = await admin.create_dm()
    await dm.send("Test DM from Jambot")
```

### Reactions not detected

**Symptoms**: Admin reacts to messages, but bot doesn't respond

**Possible Causes**:
1. Missing **Reaction** intent or permission
2. Bot not tracking the message ID
3. Reaction added before message fully loaded

**Solutions**:

1. Verify bot permissions:
   - **Add Reactions** permission
   - Check Developer Portal for **Gateway Intents**

2. Check logs for reaction events:
```bash
grep "reaction" logs/jambot.log -i
```

3. Wait for message to fully load before reacting

---

## Spotify Integration

### Authentication failed

**Symptoms**: "Failed to authenticate with Spotify" error

**Possible Causes**:
1. Invalid client ID or secret
2. Expired refresh token
3. Incorrect redirect URI

**Solutions**:

1. Verify credentials:
```bash
# Check .env values
grep SPOTIFY_ .env

# Test authentication
python <<EOF
from src.spotify_client import SpotifyClient
try:
    sp = SpotifyClient()
    print("✅ Authentication successful")
except Exception as e:
    print(f"❌ Error: {e}")
EOF
```

2. Regenerate refresh token:
   - Follow [SPOTIFY_SETUP.md](SPOTIFY_SETUP.md) Step 4
   - Update `.env` with new token
   - Restart bot

3. Verify redirect URI matches exactly:
   - Spotify Dashboard → App Settings → Redirect URIs
   - Should be: `http://localhost:8888/callback`

### Song search returns no results

**Symptoms**: Bot can't find songs on Spotify

**Possible Causes**:
1. Song not available on Spotify
2. Misspelled song title
3. Region restrictions

**Solutions**:

1. Test search manually:
```python
from src.spotify_client import SpotifyClient
sp = SpotifyClient()
results = sp.search_song("Blue Moon of Kentucky", limit=5)
for r in results:
    print(f"{r['name']} - {r['artist']}")
```

2. Try variations:
   - "Will the Circle" → "Will the Circle Be Unbroken"
   - Check `SONG_VARIATIONS` in `src/spotify_client.py`

3. Manual override:
   - Search Spotify app/web manually
   - Reply to bot DM with Spotify track link

### Rate limit errors

**Symptoms**: "429 Too Many Requests" errors

**Possible Causes**:
1. Too many API calls in short time
2. Large setlists (>50 songs)

**Solutions**:

Bot includes automatic retry logic, but you can:

1. Check retry logs:
```bash
grep "Rate limited" logs/jambot.log
```

2. Reduce concurrent requests (edit `spotify_client.py`):
```python
# Add delay between searches
import time
time.sleep(0.5)  # 500ms between searches
```

3. Split large setlists into multiple smaller ones

### Playlist creation fails

**Symptoms**: Songs validated but playlist not created

**Possible Causes**:
1. Insufficient Spotify permissions
2. Network timeout
3. Invalid track URIs

**Solutions**:

1. Verify scopes:
```python
# Check token scopes
from src.spotify_client import SpotifyClient
sp = SpotifyClient()
print(sp.sp.auth_manager.scope)
# Should include: playlist-modify-public playlist-modify-private
```

2. Check logs for specific error:
```bash
grep "playlist" logs/jambot.log -i | tail -20
```

3. Test playlist creation manually:
```python
from src.spotify_client import SpotifyClient
sp = SpotifyClient()
playlist = sp.create_playlist("Test Playlist")
print(f"Created: {playlist['url']}")
```

---

## Database Issues

### Database initialization fails

**Symptoms**: "Failed to initialize database" error

**Possible Causes**:
1. Directory permissions
2. Disk space full
3. Invalid database path

**Solutions**:

1. Check permissions:
```bash
ls -la data/
# Should be writable by bot user

# Fix permissions
chmod 700 data/
```

2. Check disk space:
```bash
df -h
```

3. Verify path:
```bash
grep DATABASE_PATH .env
# Should be absolute path to writable location
```

### Database locked error

**Symptoms**: "database is locked" error

**Possible Causes**:
1. Multiple processes accessing database
2. Stale lock file
3. File system issues

**Solutions**:

1. Ensure only one bot instance is running:
```bash
ps aux | grep jambot
# Kill extra processes if found
```

2. Remove lock file:
```bash
rm data/jambot.db-wal data/jambot.db-shm
```

3. Check database integrity:
```bash
sqlite3 data/jambot.db "PRAGMA integrity_check;"
```

### Data not persisting

**Symptoms**: Song versions not remembered between restarts

**Possible Causes**:
1. Database file not in persistent volume
2. Container data directory not mounted
3. Database writes failing silently

**Solutions**:

1. Verify volume mount (Docker):
```bash
docker-compose config
# Check volumes section

docker inspect jambot | grep Mounts -A 10
```

2. Check database writes:
```bash
# Monitor database file
watch -n 1 'ls -lh data/jambot.db'
# File size should increase after adding songs
```

3. Test database directly:
```bash
sqlite3 data/jambot.db "SELECT COUNT(*) FROM songs;"
```

---

## Deployment Issues

### Container won't start

**Symptoms**: Docker container exits immediately

**Possible Causes**:
1. Missing environment variables
2. Invalid Dockerfile
3. Dependency installation failure

**Solutions**:

1. Check container logs:
```bash
docker-compose logs jambot

# Or for specific container
docker logs jambot
```

2. Verify environment variables:
```bash
docker-compose config
# Check that all required env vars are set
```

3. Test locally first:
```bash
# Build without cache
docker-compose build --no-cache

# Run interactively
docker-compose run jambot /bin/bash
```

### DigitalOcean deployment fails

**Symptoms**: App Platform deployment fails or crashes

**Possible Causes**:
1. Image not in registry
2. Missing environment variables
3. Resource limits too low

**Solutions**:

1. Verify image in registry:
```bash
doctl registry repository list-tags jambot
```

2. Check environment variables:
```bash
doctl apps get APP_ID --format JSON | jq '.spec.services[0].envs'
```

3. Review deployment logs:
```bash
doctl apps logs APP_ID --follow
```

4. Increase resources (edit `app.yaml`):
```yaml
instance_size_slug: basic-xs  # Upgrade from basic-xxs
```

### Volume mount issues

**Symptoms**: Database not persisting in deployed container

**Possible Causes**:
1. Volume not attached
2. Wrong mount path
3. Volume permissions

**Solutions**:

1. Verify volume in app spec:
```yaml
volumes:
  - name: jambot-data
    mount_path: /app/data
```

2. Match mount path with `DATABASE_PATH`:
```bash
# In app env vars
DATABASE_PATH=/app/data/jambot.db
```

3. Check volume status:
```bash
doctl compute volume list
```

---

## Performance Issues

### Slow response time

**Symptoms**: Bot takes a long time to process setlists

**Possible Causes**:
1. Large setlist (many songs)
2. Slow Spotify API responses
3. Database query performance

**Solutions**:

1. Enable debug logging to identify bottleneck:
```bash
# In .env
LOG_LEVEL=DEBUG

# Check logs for timing
grep "seconds" logs/jambot.log
```

2. Optimize database queries (add indices):
```sql
CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(song_title);
```

3. Consider caching Spotify search results

### High memory usage

**Symptoms**: Container OOM (out of memory) errors

**Possible Causes**:
1. Large message history in memory
2. Memory leak
3. Too many concurrent operations

**Solutions**:

1. Monitor memory:
```bash
# Local
docker stats jambot

# DigitalOcean
doctl apps get APP_ID --format JSON | jq '.live_url'
# View metrics in dashboard
```

2. Increase memory limit:
```yaml
# In app.yaml or docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1024M  # Increase from 512M
```

3. Restart periodically:
```bash
# Add to crontab for daily restart
0 3 * * * docker-compose restart jambot
```

---

## Common Error Messages

### "Missing required environment variables"

**Solution**: Check `.env` file has all required variables (see [Configuration](README.md#configuration))

### "Invalid Spotify track URL"

**Solution**: Ensure URL format is `https://open.spotify.com/track/TRACK_ID`

### "Could not find admin user"

**Solution**: Verify `DISCORD_ADMIN_ID` is correct and bot can access the user

### "Failed to create playlist"

**Solution**: Check Spotify authentication and permissions (scopes)

### "Database transaction failed"

**Solution**: Check database file permissions and disk space

### "Discord API error: 50007"

**Solution**: "Cannot send messages to this user" - Check admin's DM privacy settings

### "Discord API error: 50013"

**Solution**: "Missing Permissions" - Add required bot permissions in Discord server

### "HTTPException: 429 Too Many Requests"

**Solution**: Rate limited - bot will automatically retry with backoff

---

## Getting Help

If you can't resolve an issue:

1. **Gather information**:
```bash
# Get bot logs
tail -100 logs/jambot.log > issue_logs.txt

# Get system info
docker --version
python --version
uname -a

# Get bot config (redact sensitive values)
grep -v "TOKEN\|SECRET" .env
```

2. **Check documentation**:
   - [README](README.md)
   - [Setup Guides](README.md#documentation)
   - [Admin Guide](ADMIN_GUIDE.md)

3. **Test components individually**:
   - Discord authentication
   - Spotify authentication
   - Database operations
   - Message parsing

4. **Report the issue**:
   - Include error messages
   - Describe steps to reproduce
   - Share relevant logs (redacted)
   - Note bot version and environment

---

## Debugging Tips

### Enable Verbose Logging

```bash
# In .env
LOG_LEVEL=DEBUG

# Restart bot
docker-compose restart
```

### Test Individual Components

```python
# Test config
from src.config import Config
Config.validate()

# Test database
from src.database import Database
db = Database()
print(db.get_song_by_title("Test Song"))

# Test Spotify
from src.spotify_client import SpotifyClient
sp = SpotifyClient()
results = sp.search_song("Blue Moon of Kentucky")

# Test parser
from src.setlist_parser import SetlistParser
parser = SetlistParser()
print(parser.is_setlist_message("Here's the setlist for the 7pm jam on 11/18/2024."))
```

### Monitor in Real-Time

```bash
# Follow logs
tail -f logs/jambot.log

# Watch database
watch -n 2 'sqlite3 data/jambot.db "SELECT COUNT(*) FROM songs;"'

# Monitor container
docker stats jambot
```

### Database Inspection

```bash
# Open database
sqlite3 data/jambot.db

# Useful queries
SELECT * FROM songs ORDER BY last_used DESC LIMIT 10;
SELECT * FROM setlists ORDER BY created_at DESC LIMIT 5;
SELECT COUNT(*) FROM setlist_songs;
.schema
```

---

## Prevention Tips

1. **Regular backups**: Backup `data/jambot.db` regularly
2. **Monitor logs**: Review logs weekly for warnings/errors
3. **Update dependencies**: Keep Python packages updated
4. **Test changes**: Test in development before deploying
5. **Document issues**: Keep notes on solutions for recurring problems

## Still Need Help?

- Review the source code in `src/`
- Check GitHub Issues (if repository is public)
- Contact your system administrator
- Consult Discord and Spotify API documentation
