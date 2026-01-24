---
title: Spotify Setup
description: Connect your Spotify account to JamBot
---

This guide walks you through setting up Spotify authentication for JamBot.

## Overview

JamBot uses Spotify's **Authorization Code Flow** to:
- Search for songs on Spotify
- Create playlists from setlists
- Add songs to playlists

## Prerequisites

1. **Spotify Account**: You need a Spotify account (free or premium)
2. **Spotify Developer App**: Create one at the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)

## Step 1: Create a Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click **"Create App"**
3. Fill in the details:
   - **App name**: JamBot
   - **App description**: Discord bot for creating jam session playlists
   - **Redirect URI**: `http://localhost:8888/callback`
4. Accept the Terms of Service
5. Click **"Save"**

## Step 2: Get Your Credentials

1. In your app's dashboard, click **"Settings"**
2. Copy your **Client ID**
3. Click **"View client secret"** and copy your **Client Secret**

## Step 3: Configure the Bot

### Option 1: Via Discord Modal (Recommended)

1. Run `/jambot-setup` in Discord
2. Enter your Spotify Client ID and Client Secret
3. Run `/jambot-spotify-setup` to authorize

### Option 2: Via Environment Variables

Add to your `.env` file:

```bash
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
```

## Step 4: Authorize Spotify

### For Local Development

Run the setup script:

```bash
python scripts/setup_spotify_auth.py
```

The script will:
1. Start a local web server to receive the OAuth callback
2. Open your browser to authorize JamBot
3. Exchange the authorization code for tokens
4. Save tokens to the database

### For Production (DigitalOcean)

1. Run `/jambot-spotify-setup` in Discord
2. Click the link sent via DM
3. Authorize JamBot with your Spotify account
4. Tokens are automatically saved

## Verify Success

Check the logs for:

```
INFO - Spotify authentication successful
INFO - Spotify client initialized for user: your_user_id
```

## How Token Refresh Works

- **Access tokens** expire after 1 hour
- JamBot automatically refreshes tokens using the **refresh token**
- Refresh tokens are stored in the database
- You shouldn't need to re-authorize unless:
  - You revoke access in Spotify settings
  - Your refresh token expires (rare)
  - You delete the database

## Troubleshooting

### "No Spotify tokens found"

**Problem**: You haven't completed the authorization flow.

**Solution**: Run `/jambot-spotify-setup` or `python scripts/setup_spotify_auth.py`

### "Token refresh failed"

**Problem**: Your refresh token has expired.

**Solution**: Re-authorize by running the setup again.

### Port 8888 Already in Use

**Solution**: Change the redirect URI:
1. Update your Spotify app settings
2. Update your `.env` file
3. Restart and re-authorize

## Security Notes

- Tokens are stored securely in the database
- The database file should be protected with appropriate file permissions
- Never share your tokens or client secret
- Each Discord server can have its own Spotify credentials

## Next Steps

- [Configure advanced settings](/setup/configuration/)
- [Learn about the admin workflow](/guides/admin-guide/)
