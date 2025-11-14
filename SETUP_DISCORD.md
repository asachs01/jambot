# Discord Bot Setup Guide

This guide walks you through creating a Discord bot and obtaining the necessary credentials for Jambot.

## Prerequisites

- A Discord account
- Server Administrator permissions (to add the bot to your server)

## Step 1: Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Enter a name for your application (e.g., "Jambot")
4. Accept the Terms of Service
5. Click **"Create"**

## Step 2: Create the Bot User

1. In your application, navigate to the **"Bot"** section in the left sidebar
2. Click **"Add Bot"**
3. Confirm by clicking **"Yes, do it!"**
4. Your bot is now created!

### Configure Bot Settings

1. **Username**: Set your bot's username (e.g., "Jambot")
2. **Icon**: Upload an icon for your bot (optional)
3. **Public Bot**: Toggle OFF if you want only you to add the bot to servers

## Step 3: Get Your Bot Token

1. In the **"Bot"** section, find the **"TOKEN"** section
2. Click **"Reset Token"**
3. Click **"Yes, do it!"** to confirm
4. **Copy the token** that appears (you'll need this for your `.env` file)

⚠️ **IMPORTANT**: Never share your bot token publicly! Treat it like a password.

## Step 4: Enable Required Intents

Discord requires you to enable specific "Privileged Gateway Intents" for your bot to function properly.

1. Scroll down to **"Privileged Gateway Intents"**
2. Enable the following intents:
   - ✅ **Message Content Intent** (required to read message content)
   - ✅ **Server Members Intent** (required if using member-specific features)
3. Click **"Save Changes"**

## Step 5: Configure OAuth2 Permissions

1. Navigate to the **"OAuth2"** section in the left sidebar
2. Click on **"URL Generator"**

### Select Scopes

In the **"Scopes"** section, check:
- ✅ `bot`

### Select Bot Permissions

In the **"Bot Permissions"** section that appears below, check:
- ✅ **Send Messages** - To post playlist links
- ✅ **Read Messages/View Channels** - To monitor setlist messages
- ✅ **Add Reactions** - To add reaction emojis for approval workflow
- ✅ **Send Messages in Threads** - If your server uses threads
- ✅ **Read Message History** - To process setlist messages

### Generated URL

Copy the **"Generated URL"** at the bottom of the page.

## Step 6: Add Bot to Your Server

1. Paste the Generated URL into your browser
2. Select the server you want to add the bot to
3. Click **"Continue"**
4. Review the permissions and click **"Authorize"**
5. Complete the CAPTCHA if prompted

Your bot should now appear in your server's member list (offline until you run it).

## Step 7: Get User IDs

You need to get the Discord User IDs for:
- The jam leader (who posts setlists)
- The admin (who approves song selections)

### Enable Developer Mode

1. Open Discord
2. Click the **gear icon** (User Settings) at the bottom left
3. Go to **"Advanced"** in the left sidebar under "App Settings"
4. Enable **"Developer Mode"**

### Copy User IDs

1. Right-click on the jam leader's username or avatar
2. Click **"Copy User ID"** (it will look like `123456789012345678`)
3. Repeat for the admin user

## Step 8: Add Credentials to .env

Add the following to your `.env` file:

```bash
# Discord Bot Token (from Step 3)
DISCORD_BOT_TOKEN=your_bot_token_here

# Jam Leader User ID (from Step 7)
DISCORD_JAM_LEADER_ID=123456789012345678

# Admin User ID (from Step 7)
DISCORD_ADMIN_ID=123456789012345678
```

⚠️ **Never commit `.env` to version control!** It's included in `.gitignore`.

## Troubleshooting

### Bot shows as offline

- Ensure you've started the bot (`python -m src.main`)
- Check that your bot token is correct in `.env`
- Verify your network allows WebSocket connections

### Bot can't read messages

- Ensure **Message Content Intent** is enabled (Step 4)
- Verify the bot has **Read Messages/View Channels** permission
- Check that the bot can access the channel where setlists are posted

### Bot can't send DMs

- The bot and admin user must share a server
- The admin user must allow DMs from server members
- Check admin's privacy settings: User Settings → Privacy & Safety → Allow direct messages from server members

### Missing Permissions Error

- Re-generate the invite URL with correct permissions (Step 5)
- Remove the bot from the server
- Re-add it using the new URL

## Testing Your Bot

Once configured, test that:

1. ✅ Bot appears online in your server
2. ✅ Bot responds to test messages (check logs)
3. ✅ Bot can send DMs to admin user
4. ✅ Bot can add reactions to messages

## Next Steps

- [Set up Spotify API credentials](SETUP_SPOTIFY.md)
- [Configure and run the bot](README.md#quick-start)
- [Learn about the admin workflow](ADMIN_GUIDE.md)

## Additional Resources

- [Discord Developer Documentation](https://discord.com/developers/docs/intro)
- [discord.py Documentation](https://discordpy.readthedocs.io/)
- [Discord Permissions Calculator](https://discordapi.com/permissions.html)
