# Jambot Configuration Guide

## Overview

Jambot now supports **modal-based configuration** via Discord slash commands! This allows server administrators to configure jam leaders and song approvers directly through Discord, without needing to edit environment variables.

## Configuration Methods

### Method 1: Modal-Based Configuration (Recommended)

Use Discord slash commands to configure the bot directly in your server:

#### Step 1: Get User IDs

Use the `/jambot-getid` command to get Discord user IDs:

```
/jambot-getid @username
```

This will show you the user's ID. Copy the ID for the next step.

#### Step 2: Create Spotify Developer App

Before configuring Jambot, create a Spotify Developer app:

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click "Create App"
3. Fill in App Name (e.g., "MyServer JamBot") and Description
4. Add Redirect URI: `https://your-jambot-domain.com/callback`
5. Save and copy your **Client ID** and **Client Secret**

⚠️ **Important**: Each Discord server needs its own Spotify Developer app to avoid rate limiting.

#### Step 3: Configure Jambot Essential Settings

Administrators can use the `/jambot-setup` command to configure all essential settings:

```
/jambot-setup
```

This opens a modal with five fields:

- **Jam Leader User IDs**: Users who can post setlists (comma-separated)
- **Song Approver User IDs**: Users who can approve songs (comma-separated)
- **Spotify Client ID**: From your Spotify Developer Dashboard
- **Spotify Client Secret**: From your Spotify Developer Dashboard (stored securely)
- **Spotify Redirect URI**: Leave blank to use default web server URL

**Example:**
```
Jam Leaders: 123456789012345678, 987654321098765432
Approvers: 111222333444555666, 777888999000111222
Client ID: abc123def456...
Client Secret: xyz789uvw012...
Redirect URI: (leave blank for default)
```

#### Step 4: Authorize Spotify

After configuring essential settings, authorize Spotify:

```
/jambot-spotify-setup
```

This sends you a private authorization link. Click it to connect your Spotify account.

#### Step 5: Configure Advanced Settings (Optional)

For playlist channel and name template customization:

```
/jambot-settings
```

This opens a modal with optional fields:
- **Playlist Channel ID**: Channel where playlists should be posted (optional)
- **Playlist Name Template**: Custom template using {date} and {time} placeholders (optional)

#### Features:
- ✅ Per-server Spotify apps (avoids rate limiting)
- ✅ Multiple jam leaders and approvers supported
- ✅ Real-time validation of user IDs and Spotify credentials
- ✅ Configuration stored per-server in database
- ✅ No bot restart required
- ✅ Admin-only access
- ✅ Separate advanced settings for optional customization

### Method 2: Environment Variables (Legacy)

You can still use environment variables for initial configuration or as a fallback:

```env
# .env file
DISCORD_JAM_LEADER_ID="123456789012345678"
DISCORD_ADMIN_ID="987654321098765432"
```

**Note:** The bot will use database configuration if available, falling back to environment variables only if no configuration exists in the database.

## Permissions

Only users with **Administrator** permissions in the Discord server can run `/jambot-setup`.

## How It Works

1. **Jam Leaders** can post setlist messages that the bot will detect and process
2. **Approvers** receive DM workflows to approve songs and create Spotify playlists
3. When a jam leader posts a setlist:
   - Bot detects and parses the message
   - Searches for songs on Spotify
   - Sends approval workflow to ALL configured approvers
   - Creates playlist when approved

## Database Storage

Configuration is stored in the SQLite database in the `bot_configuration` table:

```sql
CREATE TABLE bot_configuration (
    id INTEGER PRIMARY KEY,
    guild_id INTEGER UNIQUE NOT NULL,
    jam_leader_ids TEXT NOT NULL,           -- JSON array
    approver_ids TEXT NOT NULL,             -- JSON array
    channel_id INTEGER,                     -- Optional playlist channel
    playlist_name_template TEXT,            -- Optional custom template
    spotify_client_id TEXT,                 -- Per-guild Spotify app
    spotify_client_secret TEXT,             -- Per-guild Spotify secret
    spotify_redirect_uri TEXT,              -- Per-guild redirect URI
    updated_at TIMESTAMP NOT NULL,
    updated_by INTEGER NOT NULL
);
```

## Migration from Environment Variables

If you're currently using environment variables:

1. Keep your `.env` file as-is for bot token and Spotify credentials
2. Run `/jambot-setup` in your Discord server to configure jam leaders and approvers
3. The bot will now use the database configuration
4. You can optionally remove `DISCORD_JAM_LEADER_ID` and `DISCORD_ADMIN_ID` from `.env`

## Troubleshooting

### "You need administrator permissions to use this command"
- Make sure you have the Administrator role in your Discord server
- Check your server role settings

### "The following user IDs are invalid..."
- Verify the user IDs are correct
- Make sure the users are members of your Discord server
- Use `/jambot-getid @username` to get the correct ID

### "No approvers configured for this guild"
- Run `/jambot-setup` to configure approvers
- Make sure you entered at least one approver ID

### Configuration not taking effect
- Try re-running `/jambot-setup` to update the configuration
- Check the bot logs for any error messages
- Verify the database file exists and is writable

## Examples

### Configure Multiple Jam Leaders

If you have 3 people who post setlists:

1. Get each person's ID: `/jambot-getid @person1`, `/jambot-getid @person2`, `/jambot-getid @person3`
2. Run `/jambot-setup`
3. Enter: `123456789, 234567890, 345678901` in the Jam Leaders field

### Configure Multiple Approvers

If you want 2 people to approve songs:

1. Get their IDs: `/jambot-getid @approver1`, `/jambot-getid @approver2`
2. Run `/jambot-setup`
3. Enter: `111222333, 444555666` in the Approvers field

## Best Practices

1. **Have at least 2 approvers** for redundancy
2. **Test the configuration** by posting a test setlist
3. **Keep your `.env` file secure** - it still contains sensitive Spotify credentials
4. **Regularly review** who has jam leader and approver access

## Premium Environment Variables

JamBot supports premium AI chord chart generation through an optional Premium API service. Add these variables to enable premium features:

```env
# Premium API Configuration
PREMIUM_API_BASE_URL=https://api.premium.jambot.io
PREMIUM_API_TIMEOUT=60
```

### Variable Details

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PREMIUM_API_BASE_URL` | string | `https://api.premium.jambot.io` | Base URL for the JamBot Premium API. Only change for self-hosted instances. |
| `PREMIUM_API_TIMEOUT` | integer | `60` | Request timeout in seconds. AI generation can take time; keep at 30+ seconds. |

### How It Works

1. **Configuration**: Set the environment variables above
2. **Setup**: Server admins run `/jambot-premium-setup` with their API token
3. **Validation**: Token is validated with the Premium API and securely hashed
4. **Usage**: Users can create AI chord charts using `/jambot-chart create`
5. **Credits**: Each generation uses 1 credit; purchase more via `/jambot-buy-credits`

### Premium Commands

| Command | Description | Permission |
|---------|-------------|------------|
| `/jambot-premium-setup` | Configure premium API token | Admin only |
| `/jambot-credits` | View credit balance | Everyone |
| `/jambot-buy-credits` | Purchase credit packs | Everyone |
| `/jambot-chart create` | Create AI chord chart | Everyone (requires credits) |

### Related Files

- `src/config.py` - Premium configuration constants
- `src/premium_client.py` - HTTP client for Premium API (`PremiumClient` class)
- `src/commands.py` - Premium Discord commands
- `.env.example` - Example environment variables

## Support

If you encounter issues:

1. Check the bot logs in `/app/logs/jambot.log`
2. Verify your database exists and is accessible
3. Review the TROUBLESHOOTING.md document
4. Open an issue on GitHub with logs and error messages
