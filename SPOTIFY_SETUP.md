# Spotify OAuth Setup Guide

This guide walks you through setting up Spotify authentication for Jambot using the proper OAuth flow.

## Overview

Jambot uses Spotify's **Authorization Code Flow** to:
- Search for songs on Spotify
- Create playlists from setlists
- Add songs to playlists

The OAuth flow requires one-time setup to authorize Jambot with your Spotify account.

## Prerequisites

1. **Spotify Account**: You need a Spotify account (free or premium)
2. **Spotify Developer App**: You should already have this from the initial setup
   - Client ID and Client Secret should be in your `.env` file

## Step 1: Verify Spotify App Settings

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click on your Jambot application
3. Click **Settings**
4. Under **Redirect URIs**, ensure `http://localhost:8888/callback` is listed
   - If not, click **Add** and enter: `http://localhost:8888/callback`
   - Click **Save**

## Step 2: Run the Setup Script

The setup script will:
1. Start a local web server to receive the OAuth callback
2. Open your browser to authorize Jambot
3. Exchange the authorization code for access and refresh tokens
4. Save tokens to the database

**Run the script:**

```bash
python scripts/setup_spotify_auth.py
```

Or if using virtualenv:

```bash
source .venv/bin/activate  # or your virtualenv path
python scripts/setup_spotify_auth.py
```

## Step 3: Authorize in Browser

1. The script will automatically open your browser
2. Log in to Spotify if needed
3. Review the permissions Jambot is requesting:
   - **Manage your playlists** (to create and modify playlists)
4. Click **Agree** to authorize
5. You'll see a success message in the browser
6. Return to the terminal

## Step 4: Verify Success

The script will show:

```
✅ Successfully obtained tokens!
✅ Setup complete!

Tokens have been saved to the database.
You can now restart Jambot to use the new tokens.
```

## Step 5: Restart the Bot

```bash
docker compose restart
```

Or if running locally:

```bash
# Stop the bot (Ctrl+C)
python -m src.main
```

## Verify It's Working

Check the logs:

```bash
docker compose logs -f
```

You should see:

```
INFO - Loading Spotify tokens from database...
INFO - Using cached access token
INFO - Spotify authentication successful
INFO - Spotify client initialized for user: your_user_id
```

## Troubleshooting

### "No Spotify tokens found in database"

**Problem**: You haven't run the setup script yet.

**Solution**: Run `python scripts/setup_spotify_auth.py`

### "Failed to receive authorization code"

**Possible causes**:
- You denied authorization in the browser
- The redirect URI doesn't match your Spotify app settings
- The request timed out

**Solution**:
1. Verify redirect URI is `http://localhost:8888/callback` in your Spotify app settings
2. Run the setup script again
3. Complete authorization within 60 seconds

### "Token refresh failed"

**Problem**: Your refresh token has expired (rare, but can happen).

**Solution**: Run the setup script again to get new tokens:
```bash
python scripts/setup_spotify_auth.py
```

### Port 8888 already in use

**Problem**: Another application is using port 8888.

**Solution**: Change the redirect URI in:
1. Your Spotify app settings (e.g., to `http://localhost:8889/callback`)
2. Your `.env` file: `SPOTIFY_REDIRECT_URI=http://localhost:8889/callback`
3. Restart the bot and run the setup script again

## How Token Refresh Works

- **Access tokens** expire after 1 hour
- Jambot automatically refreshes the access token using the **refresh token**
- Refresh tokens are long-lived and stored in the database
- You shouldn't need to re-authorize unless:
  - You revoke access in your Spotify account settings
  - Your refresh token expires (rare)
  - You delete the database file

## Security Notes

- Tokens are stored in the database file (`data/jambot.db`)
- The database file should be protected with appropriate file permissions
- Never share your tokens or database file
- The client secret should never be exposed in client-side code

## Re-authorizing

If you need to re-authorize (e.g., token expired), simply run the setup script again:

```bash
python scripts/setup_spotify_auth.py
```

This will:
- Overwrite existing tokens
- Generate fresh access and refresh tokens
- Update the database

---

**Need Help?** See the full troubleshooting guide in `TROUBLESHOOTING.md`
