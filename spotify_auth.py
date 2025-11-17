#!/usr/bin/env python3
"""Script to obtain Spotify refresh token for Jambot.

This script will help you complete the OAuth flow to get a refresh token
that Jambot can use to access your Spotify account.

Prerequisites:
1. Created a Spotify app in the Spotify Developer Dashboard
2. Added redirect URI: http://127.0.0.1:8888/callback
3. Have your Client ID and Client Secret ready
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth

print("=" * 60)
print("Jambot Spotify Authentication")
print("=" * 60)
print()

# Get credentials from user
print("Enter your Spotify app credentials:")
print("(You can find these in the Spotify Developer Dashboard)")
print()

CLIENT_ID = input("Client ID: ").strip()
CLIENT_SECRET = input("Client Secret: ").strip()

# Fixed redirect URI (must match Spotify app settings)
REDIRECT_URI = "http://127.0.0.1:8888/callback"

# Required scopes for Jambot
SCOPES = "playlist-modify-public playlist-modify-private user-read-private"

print()
print("-" * 60)
print("Configuration:")
print(f"  Client ID: {CLIENT_ID[:10]}...")
print(f"  Redirect URI: {REDIRECT_URI}")
print(f"  Scopes: {SCOPES}")
print("-" * 60)
print()

# Initialize OAuth
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPES,
    open_browser=True  # Automatically open browser
)

# Get the authorization URL
auth_url = sp_oauth.get_authorize_url()

print("STEP 1: Authorize the application")
print("-" * 60)
print("A browser window will open (or copy this URL):")
print()
print(auth_url)
print()
print("After authorizing, you'll be redirected to a URL like:")
print(f"{REDIRECT_URI}?code=XXXXXXX")
print()
print("If the page shows an error (can't connect), that's OK!")
print("Just copy the FULL URL from your browser's address bar.")
print("-" * 60)
print()

# User will be redirected to REDIRECT_URI with a 'code' parameter
redirect_response = input("Paste the FULL redirect URL here: ").strip()

# Extract the authorization code from the URL
try:
    print()
    print("STEP 2: Exchanging code for tokens...")
    print("-" * 60)

    code = sp_oauth.parse_response_code(redirect_response)
    token_info = sp_oauth.get_access_token(code, as_dict=True, check_cache=False)

    print("✅ SUCCESS!")
    print("-" * 60)
    print()
    print("Add these to your .env file:")
    print()
    print(f"SPOTIFY_CLIENT_ID={CLIENT_ID}")
    print(f"SPOTIFY_CLIENT_SECRET={CLIENT_SECRET}")
    print(f"SPOTIFY_REDIRECT_URI={REDIRECT_URI}")
    print(f"SPOTIFY_REFRESH_TOKEN={token_info['refresh_token']}")
    print()
    print("-" * 60)

    # Test the token
    print()
    print("STEP 3: Testing authentication...")
    print("-" * 60)

    sp = spotipy.Spotify(auth_manager=sp_oauth)
    user = sp.current_user()

    print(f"✅ Authenticated as: {user['display_name']}")
    print(f"   Spotify User ID: {user['id']}")
    print(f"   Email: {user.get('email', 'N/A')}")
    print()
    print("=" * 60)
    print("Setup complete! Your bot is ready to create playlists.")
    print("=" * 60)

except Exception as e:
    print()
    print("❌ ERROR")
    print("-" * 60)
    print(f"Error: {e}")
    print()
    print("Common issues:")
    print("  - Make sure you copied the FULL URL from the browser")
    print("  - Verify your Client ID and Secret are correct")
    print("  - Check that redirect URI matches: http://127.0.0.1:8888/callback")
    print("  - Ensure the app has the correct scopes in Spotify Dashboard")
    print()
    print("See SETUP_SPOTIFY.md for detailed troubleshooting.")
