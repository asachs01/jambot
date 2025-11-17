#!/usr/bin/env python3
"""Interactive Spotify OAuth setup script for Jambot.

This script helps you authorize Jambot with Spotify and saves the tokens to the database.
It should be run on the host machine (not inside Docker).
"""

import os
import sys
import time
import base64
import webbrowser
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests library not found. Install it with: pip install requests")
    sys.exit(1)


# Load config from .env file
class Config:
    """Minimal config loader for Spotify credentials."""

    def __init__(self):
        env_file = Path(__file__).parent.parent / ".env"
        if not env_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {env_file}\n"
                "Please create a .env file with your Spotify credentials."
            )

        # Load environment variables
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    # Split on first = only
                    key, value = line.split("=", 1)
                    # Strip whitespace and handle inline comments
                    value = value.strip()
                    # Remove inline comments (anything after #)
                    if "#" in value:
                        value = value.split("#")[0].strip()
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value

        # Get required values
        self.SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
        self.SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
        self.SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", str(Path(__file__).parent.parent / "data" / "jambot.db"))

        # Validate
        if not self.SPOTIFY_CLIENT_ID or not self.SPOTIFY_CLIENT_SECRET:
            raise ValueError(
                "Missing Spotify credentials in .env file.\n"
                "Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET."
            )


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback from Spotify."""

    auth_code = None
    error = None

    def do_GET(self):
        """Handle GET request with authorization code or error."""
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        if 'code' in query_params:
            OAuthCallbackHandler.auth_code = query_params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <head><title>Spotify Authorization</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #1DB954;">Success!</h1>
                    <p>Jambot has been authorized with Spotify.</p>
                    <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
            """)
        elif 'error' in query_params:
            OAuthCallbackHandler.error = query_params['error'][0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
                <html>
                <head><title>Spotify Authorization Failed</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #e22134;">Authorization Failed</h1>
                    <p>Error: {query_params['error'][0]}</p>
                    <p>Please return to the terminal and try again.</p>
                </body>
                </html>
            """.encode())
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Invalid callback')

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def exchange_code_for_tokens(auth_code: str, config) -> dict:
    """Exchange authorization code for access and refresh tokens."""
    credentials = f"{config.SPOTIFY_CLIENT_ID}:{config.SPOTIFY_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    token_url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": config.SPOTIFY_REDIRECT_URI,
    }

    response = requests.post(token_url, headers=headers, data=data, timeout=10)
    response.raise_for_status()

    return response.json()


def save_tokens_to_db(access_token: str, refresh_token: str, expires_in: int, db_path: str):
    """Save tokens to the database."""
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    expires_at = int(time.time()) + expires_in

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spotify_tokens (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            updated_at INTEGER DEFAULT (strftime('%s', 'now'))
        )
    """)

    cursor.execute("""
        INSERT OR REPLACE INTO spotify_tokens
        (id, access_token, refresh_token, expires_at, updated_at)
        VALUES (1, ?, ?, ?, strftime('%s', 'now'))
    """, (access_token, refresh_token, expires_at))

    conn.commit()
    conn.close()

    print(f"✓ Tokens saved to database: {db_path}")


def main():
    """Run interactive Spotify OAuth setup."""
    print("=" * 70)
    print("Jambot Spotify OAuth Setup")
    print("=" * 70)
    print()

    try:
        config = Config()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print("Configuration:")
    print(f"  Client ID: {config.SPOTIFY_CLIENT_ID[:20]}...")
    print(f"  Redirect URI: {config.SPOTIFY_REDIRECT_URI}")
    print(f"  Database: {config.DATABASE_PATH}")
    print()

    scopes = "playlist-modify-public playlist-modify-private user-read-private"
    auth_url = (
        f"https://accounts.spotify.com/authorize"
        f"?client_id={config.SPOTIFY_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={config.SPOTIFY_REDIRECT_URI}"
        f"&scope={scopes.replace(' ', '%20')}"
        f"&show_dialog=true"
    )

    print("Step 1: Starting local callback server...")
    port = 8888
    try:
        server = HTTPServer(('127.0.0.1', port), OAuthCallbackHandler)
        print(f"✓ Server listening on http://127.0.0.1:{port}/callback")
        print()
    except OSError as e:
        print(f"ERROR: Failed to start server on port {port}: {e}")
        print("Make sure no other application is using this port.")
        sys.exit(1)

    print("Step 2: Opening browser for Spotify authorization...")
    print()
    print("A browser window will open. Please:")
    print("  1. Log in to Spotify (if not already logged in)")
    print("  2. Click 'Agree' to authorize Jambot")
    print("  3. You will be redirected back automatically")
    print()

    input("Press Enter to open browser...")
    webbrowser.open(auth_url)

    print("Waiting for authorization...")
    server.handle_request()

    if OAuthCallbackHandler.error:
        print(f"\nERROR: Authorization failed: {OAuthCallbackHandler.error}")
        sys.exit(1)

    if not OAuthCallbackHandler.auth_code:
        print("\nERROR: No authorization code received")
        sys.exit(1)

    print("✓ Authorization code received")
    print()

    print("Step 3: Exchanging authorization code for tokens...")
    try:
        tokens = exchange_code_for_tokens(OAuthCallbackHandler.auth_code, config)
        print("✓ Tokens received from Spotify")
        print()
    except requests.RequestException as e:
        print(f"ERROR: Failed to exchange code for tokens: {e}")
        sys.exit(1)

    print("Step 4: Saving tokens to database...")
    try:
        save_tokens_to_db(
            tokens['access_token'],
            tokens['refresh_token'],
            tokens['expires_in'],
            config.DATABASE_PATH
        )
    except Exception as e:
        print(f"ERROR: Failed to save tokens: {e}")
        sys.exit(1)

    print()
    print("=" * 70)
    print("✓ Setup Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Restart Jambot: docker compose restart")
    print("  2. Post a setlist in Discord")
    print("  3. Jambot will create a Spotify playlist automatically")
    print()
    print("Your tokens will automatically refresh when they expire.")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
