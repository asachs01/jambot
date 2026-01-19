---
title: Troubleshooting
description: Common issues and solutions for JamBot
---

This guide covers common issues with JamBot and their solutions.

## Quick Diagnosis: Bot Not Detecting Messages

If your bot is **online** but **not responding** to messages:

### Step 1: Verify Message Content Intent

**This is the #1 reason bots don't detect messages.**

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your JamBot application
3. Click **"Bot"** in the left sidebar
4. Scroll down to **"Privileged Gateway Intents"**
5. Ensure **"Message Content Intent"** is toggled **ON**
6. Click **"Save Changes"**
7. **Restart your bot**

:::caution
The intent MUST be enabled in the Developer Portal, not just in code.
:::

### Step 2: Verify Your User ID

The bot only responds to configured jam leader user IDs.

1. Enable Developer Mode: Discord Settings → Advanced → Developer Mode ON
2. Right-click your username → Copy User ID
3. Use `/jambot-setup` to add yourself as a jam leader

### Step 3: Verify Bot Can See the Channel

1. Look at the member list on the right side of the channel
2. Find **JamBot** in the list
3. If not there: Right-click channel → Edit Channel → Permissions → Add JamBot

### Step 4: Test Message Format

Use this exact format:

```
Here's the setlist for the 7pm jam on November 20th.

1. Will the Circle Be Unbroken
2. Rocky Top
3. Man of Constant Sorrow
```

**Requirements:**
- Line 1 must contain: `here's the setlist for the [TIME] jam on [DATE].`
- There must be a **period (.)** after the date
- Songs must be numbered: `1. Song Title`

### Step 5: Check the Logs

```bash
docker compose logs -f
```

| What You See | Problem | Solution |
|-------------|---------|----------|
| No "Received message" logs | Message Content Intent not enabled | Step 1 |
| "Received message" but wrong user ID | Not configured as jam leader | Use `/jambot-setup` |
| "Received message" but no "Detected setlist" | Message format wrong | Check Step 4 |
| "Detected setlist message" | ✅ Working! | Bot should send you a DM |

---

## Bot Status Issues

### Bot shows as offline

**Solutions:**
- Check if bot process is running
- Verify Discord token in `.env`
- Check network connectivity
- Restart the bot

### Bot connects then disconnects

**Solutions:**
1. Check Discord Developer Portal for enabled intents
2. Verify configuration is valid
3. Check database initialization

---

## Discord Integration

### Bot doesn't detect setlist messages

1. Verify jam leader ID is correct
2. Check bot permissions in channel
3. Test setlist format matches expected pattern

### Bot can't send DMs to admin

1. Verify admin User ID is correct
2. Check admin's DM privacy settings (Settings → Privacy & Safety → Allow DMs from server members)
3. Ensure bot and admin share a server

### Reactions not detected

1. Verify bot has **Add Reactions** permission
2. Wait for message to fully load before reacting
3. Check logs for reaction events

---

## Spotify Integration

### Authentication failed

1. Verify client ID and secret in configuration
2. Regenerate refresh token if expired
3. Verify redirect URI matches exactly

### Song search returns no results

1. Test search manually in Spotify
2. Try variations of the song name
3. Use manual override with direct Spotify link

### Rate limit errors

Bot includes automatic retry logic. For persistent issues:
- Check retry logs
- Add delays between searches
- Split large setlists

### Playlist creation fails

1. Verify Spotify permissions/scopes
2. Check logs for specific errors
3. Test playlist creation manually

---

## Database Issues

### Database initialization fails

1. Check directory permissions (`chmod 700 data/`)
2. Verify disk space
3. Check database path in configuration

### Database locked error

1. Ensure only one bot instance is running
2. Remove lock files: `rm data/jambot.db-wal data/jambot.db-shm`
3. Check database integrity

### Data not persisting

1. Verify volume mount in Docker
2. Check that database writes are succeeding
3. Match mount path with `DATABASE_PATH`

---

## Deployment Issues

### Container won't start

1. Check container logs
2. Verify all environment variables are set
3. Build without cache: `docker-compose build --no-cache`

### DigitalOcean deployment fails

1. Verify image in registry
2. Check environment variables in App Platform
3. Review deployment logs
4. Consider increasing resources

---

## Common Error Messages

| Error | Solution |
|-------|----------|
| "Missing required environment variables" | Check `.env` file |
| "Invalid Spotify track URL" | Use format `https://open.spotify.com/track/TRACK_ID` |
| "Could not find admin user" | Verify `DISCORD_ADMIN_ID` |
| "Failed to create playlist" | Check Spotify authentication |
| "Database transaction failed" | Check permissions and disk space |
| "Discord API error: 50007" | Admin has DMs disabled |
| "Discord API error: 50013" | Missing bot permissions |
| "429 Too Many Requests" | Rate limited - bot will auto-retry |

---

## Debugging Tips

### Enable Verbose Logging

```bash
# In .env
LOG_LEVEL=DEBUG
```

### Monitor in Real-Time

```bash
# Follow logs
tail -f logs/jambot.log

# Monitor container
docker stats jambot
```

### Test Individual Components

```python
# Test config
from src.config import Config
Config.validate()

# Test database
from src.database import Database
db = Database()

# Test Spotify
from src.spotify_client import SpotifyClient
sp = SpotifyClient()
```

---

## Prevention Tips

1. **Regular backups**: Backup `data/jambot.db` regularly
2. **Monitor logs**: Review logs weekly for warnings/errors
3. **Update dependencies**: Keep Python packages updated
4. **Test changes**: Test in development before deploying

## Still Need Help?

- Review the source code in `src/`
- Check [GitHub Issues](https://github.com/sachs7/jambot/issues)
- Consult Discord and Spotify API documentation
