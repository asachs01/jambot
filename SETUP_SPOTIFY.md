# Spotify API Setup Guide

This guide explains how to set up Spotify API credentials and obtain a refresh token for Jambot.

## Prerequisites

- A Spotify account (Free or Premium)
- Python 3.11+ installed

## Step 1: Create a Spotify App

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click **"Create app"**
4. Fill in the application details:
   - **App name**: "Jambot" (or your preferred name)
   - **App description**: "Discord bot for bluegrass jam setlists"
   - **Redirect URIs**: `http://localhost:8888/callback`
   - **Which API/SDKs are you planning to use?**: Check "Web API"
5. Agree to the Spotify Developer Terms of Service
6. Click **"Save"**

## Step 2: Get Your Client Credentials

1. Click on your newly created app to open its dashboard
2. Click **"Settings"** in the top right
3. You'll see:
   - **Client ID** - Copy this
   - **Client secret** - Click "View client secret" and copy it

⚠️ **IMPORTANT**: Never share your client secret publicly!

## Step 3: Add Redirect URI

1. In the app settings, find **"Redirect URIs"**
2. Add: `http://localhost:8888/callback`
3. Click **"Add"**
4. Click **"Save"** at the bottom of the page

## Step 4: Obtain a Refresh Token

Spotify requires OAuth 2.0 authentication. You need to complete an initial authorization flow to get a refresh token.

### Option A: Using the Authorization Script (Recommended)

Create a file called `spotify_auth.py` in your project root:

```python
"""Script to obtain Spotify refresh token."""
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Replace with your credentials
CLIENT_ID = "your_client_id_here"
CLIENT_SECRET = "your_client_secret_here"
REDIRECT_URI = "http://localhost:8888/callback"

# Required scopes for Jambot
SCOPES = "playlist-modify-public playlist-modify-private"

# Initialize OAuth
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPES
)

# Get the authorization URL
auth_url = sp_oauth.get_authorize_url()
print(f"\nPlease visit this URL to authorize the application:\n{auth_url}\n")

# User will be redirected to REDIRECT_URI with a 'code' parameter
print("After authorizing, you'll be redirected to a URL like:")
print("http://localhost:8888/callback?code=XXXXXXX")
print("\nPaste the FULL redirect URL here:")

redirect_response = input().strip()

# Extract the authorization code from the URL
try:
    code = sp_oauth.parse_response_code(redirect_response)
    token_info = sp_oauth.get_access_token(code)

    print("\n✅ Success! Add this refresh token to your .env file:")
    print(f"\nSPOTIFY_REFRESH_TOKEN={token_info['refresh_token']}")

    # Test the token
    sp = spotipy.Spotify(auth_manager=sp_oauth)
    user = sp.current_user()
    print(f"\nAuthenticated as: {user['display_name']} ({user['id']})")

except Exception as e:
    print(f"\n❌ Error: {e}")
    print("Please make sure you copied the full redirect URL.")
```

Run the script:

```bash
# Install spotipy first if not already installed
pip install spotipy

# Run the authorization script
python spotify_auth.py
```

### Option B: Manual Authorization Flow

1. Construct the authorization URL:
```
https://accounts.spotify.com/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost:8888/callback&scope=playlist-modify-public%20playlist-modify-private
```

2. Visit the URL in your browser and authorize the application
3. You'll be redirected to `http://localhost:8888/callback?code=XXXXXX`
4. Copy the `code` parameter value
5. Make a POST request to exchange the code for tokens:

```bash
curl -X POST "https://accounts.spotify.com/api/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=authorization_code" \
     -d "code=YOUR_CODE_HERE" \
     -d "redirect_uri=http://localhost:8888/callback" \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "client_secret=YOUR_CLIENT_SECRET"
```

6. The response will include a `refresh_token` field - copy this value

## Step 5: Add Credentials to .env

Add the following to your `.env` file:

```bash
# Spotify API Credentials
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
SPOTIFY_REFRESH_TOKEN=your_refresh_token_here
```

⚠️ **Never commit `.env` to version control!** It's included in `.gitignore`.

## Understanding the Credentials

### Client ID & Secret
- Identify your application to Spotify
- Used for all API requests

### Redirect URI
- Where Spotify sends the user after authorization
- Must match exactly what's configured in the Spotify Dashboard

### Refresh Token
- Long-lived token used to obtain short-lived access tokens
- Jambot automatically refreshes access tokens as needed
- **Important**: If unused for an extended period (6-12 months), refresh tokens may expire

## Required Scopes

Jambot requires these Spotify API scopes:
- `playlist-modify-public` - Create and modify public playlists
- `playlist-modify-private` - Create and modify private playlists (if needed)

## Troubleshooting

### "Invalid redirect URI" error

- Ensure the redirect URI in your app settings exactly matches what's in your code
- Common mistake: `http://localhost:8888/callback` vs `http://localhost:8888/callback/`
- Redirect URIs are case-sensitive

### "Invalid client" error

- Double-check your Client ID and Client Secret
- Ensure there are no extra spaces when copying
- Try regenerating the Client Secret in the Spotify Dashboard

### Refresh token expired

If your refresh token expires (rare, but possible if unused for months):
1. Run the authorization script again (Step 4)
2. Update your `.env` file with the new refresh token
3. Restart the bot

### Rate limit errors

Spotify API allows ~180 requests per minute:
- Jambot includes automatic retry logic with exponential backoff
- Rate limits reset every minute
- For large setlists (>50 songs), delays between API calls are normal

### Playlists not appearing

- Verify the authenticated Spotify user is correct
- Check that playlists are being created (check Spotify web/app)
- Ensure you have the correct scope permissions

## Testing Your Setup

Test your Spotify credentials with this Python script:

```python
import spotipy
from spotipy.oauth2 import SpotifyOAuth

auth_manager = SpotifyOAuth(
    client_id="your_client_id",
    client_secret="your_client_secret",
    redirect_uri="http://localhost:8888/callback",
    scope="playlist-modify-public playlist-modify-private"
)

auth_manager.token_info = {
    'refresh_token': 'your_refresh_token',
    'access_token': None,
    'expires_at': 0
}

sp = spotipy.Spotify(auth_manager=auth_manager)

# Test API access
user = sp.current_user()
print(f"✅ Authenticated as: {user['display_name']}")
print(f"Spotify User ID: {user['id']}")

# Test search
results = sp.search(q='Blue Moon of Kentucky', type='track', limit=1)
if results['tracks']['items']:
    print(f"✅ Search working: Found '{results['tracks']['items'][0]['name']}'")
```

If this script runs without errors, your Spotify setup is complete!

## Next Steps

- [Complete Discord bot setup](SETUP_DISCORD.md)
- [Run the bot](README.md#quick-start)
- [Learn about the admin workflow](ADMIN_GUIDE.md)

## Additional Resources

- [Spotify Web API Documentation](https://developer.spotify.com/documentation/web-api)
- [Spotipy Documentation](https://spotipy.readthedocs.io/)
- [Spotify API Console](https://developer.spotify.com/console/) (for testing API calls)
