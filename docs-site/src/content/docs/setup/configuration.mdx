---
title: Configuration
description: Configure JamBot using Discord slash commands
---

JamBot supports **modal-based configuration** via Discord slash commands, allowing server administrators to configure jam leaders and song approvers directly through Discord.

## Configuration Methods

### Method 1: Modal-Based Configuration (Recommended)

Use Discord slash commands to configure the bot directly in your server.

#### Step 1: Get User IDs

Use the `/jambot-getid` command to get Discord user IDs:

```
/jambot-getid @username
```

This displays the user's ID. Copy it for the next step.

#### Step 2: Configure Essential Settings

Run `/jambot-setup` (admin only) to configure:

- **Jam Leader User IDs**: Users who can post setlists (comma-separated)
- **Song Approver User IDs**: Users who can approve songs (comma-separated)
- **Spotify Client ID**: From your Spotify Developer Dashboard
- **Spotify Client Secret**: From your Spotify Developer Dashboard
- **Spotify Redirect URI**: Leave blank for default

**Example:**
```
Jam Leaders: 123456789012345678, 987654321098765432
Approvers: 111222333444555666, 777888999000111222
Client ID: abc123def456...
Client Secret: xyz789uvw012...
```

#### Step 3: Authorize Spotify

Run `/jambot-spotify-setup` to authorize with Spotify. You'll receive a private link via DM.

#### Step 4: Configure Advanced Settings (Optional)

Run `/jambot-settings` for optional customization:

- **Playlist Channel ID**: Channel where playlists should be posted
- **Playlist Name Template**: Custom template using `{date}` and `{time}` placeholders

### Method 2: Environment Variables (Legacy)

You can use environment variables as a fallback:

```env
# .env file
DISCORD_JAM_LEADER_ID="123456789012345678"
DISCORD_ADMIN_ID="987654321098765432"
```

:::note
The bot uses database configuration if available, falling back to environment variables only if no configuration exists.
:::

## Features

- ✅ Per-server Spotify apps (avoids rate limiting)
- ✅ Multiple jam leaders and approvers supported
- ✅ Real-time validation of user IDs and Spotify credentials
- ✅ Configuration stored per-server in database
- ✅ No bot restart required
- ✅ Admin-only access

## Permissions

Only users with **Administrator** permissions can run `/jambot-setup`.

## How It Works

1. **Jam Leaders** can post setlist messages that the bot will detect and process
2. **Approvers** receive DM workflows to approve songs and create Spotify playlists
3. When a jam leader posts a setlist:
   - Bot detects and parses the message
   - Searches for songs on Spotify
   - Sends approval workflow to ALL configured approvers
   - Creates playlist when approved

## Examples

### Configure Multiple Jam Leaders

If you have 3 people who post setlists:

1. Get each person's ID: `/jambot-getid @person1`, etc.
2. Run `/jambot-setup`
3. Enter: `123456789, 234567890, 345678901` in the Jam Leaders field

### Configure Multiple Approvers

1. Get their IDs using `/jambot-getid`
2. Run `/jambot-setup`
3. Enter IDs in the Approvers field

## Best Practices

1. **Have at least 2 approvers** for redundancy
2. **Test the configuration** by posting a test setlist
3. **Keep your `.env` file secure**
4. **Regularly review** who has jam leader and approver access

## Troubleshooting

### "You need administrator permissions"
Make sure you have the Administrator role in your Discord server.

### "The following user IDs are invalid..."
- Verify the user IDs are correct
- Make sure the users are members of your Discord server
- Use `/jambot-getid @username` to get the correct ID

### "No approvers configured for this guild"
Run `/jambot-setup` to configure approvers.
