"""Web server for Jambot setup and Spotify authentication."""
from flask import Flask, redirect, request, render_template_string, url_for
from src.spotify_client import SpotifyClient
from src.database import Database
from src.config import Config
from src.logger import logger
import os

app = Flask(__name__)
db = Database()

# HTML template for setup page
SETUP_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Jambot Setup</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .card {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #1DB954;
            margin-top: 0;
        }
        .status {
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .status.warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        .button {
            display: inline-block;
            padding: 12px 24px;
            background: #1DB954;
            color: white;
            text-decoration: none;
            border-radius: 24px;
            font-weight: 500;
            transition: background 0.3s;
        }
        .button:hover {
            background: #1ed760;
        }
        .info {
            background: #e7f3ff;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
            border-left: 4px solid #2196F3;
        }
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>🎵 Jambot Setup</h1>

        {% if authenticated %}
        <div class="status success">
            <strong>✅ Spotify Connected!</strong><br>
            Your bot is authenticated and ready to use.
        </div>
        <div class="info">
            <strong>Next steps:</strong>
            <ol>
                <li>Add the bot to your Discord server</li>
                <li>Use <code>/jambot-setup</code> to configure jam leaders and approvers</li>
                <li>Post a setlist and the bot will create a Spotify playlist!</li>
            </ol>
        </div>
        {% elif error %}
        <div class="status error">
            <strong>❌ Authentication Failed</strong><br>
            {{ error }}
        </div>
        <a href="/" class="button">Try Again</a>
        {% else %}
        <div class="status warning">
            <strong>⚠️ Spotify Not Connected</strong><br>
            You need to authenticate with Spotify before the bot can create playlists.
        </div>
        <div class="info">
            <strong>What this does:</strong><br>
            Clicking the button below will redirect you to Spotify to authorize Jambot to create playlists on your behalf.
            Your credentials are stored securely in the database.
        </div>
        <a href="/auth" class="button">Connect with Spotify</a>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    """Show setup page with Spotify authentication status."""
    try:
        # Check if we already have valid tokens
        spotify = SpotifyClient()
        authenticated = spotify.is_authenticated()
        return render_template_string(SETUP_TEMPLATE, authenticated=authenticated, error=None)
    except Exception as e:
        logger.error(f"Error checking authentication status: {e}", exc_info=True)
        return render_template_string(SETUP_TEMPLATE, authenticated=False, error=str(e))

@app.route('/health')
def health():
    """Health check endpoint for App Platform."""
    return {'status': 'healthy', 'service': 'jambot'}, 200

@app.route('/auth')
def auth():
    """Redirect to Spotify authorization."""
    try:
        spotify = SpotifyClient()
        auth_url = spotify.get_auth_url()
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Error generating auth URL: {e}", exc_info=True)
        return render_template_string(SETUP_TEMPLATE, authenticated=False, error=f"Failed to generate auth URL: {str(e)}")

@app.route('/callback')
def callback():
    """Handle Spotify OAuth callback."""
    try:
        code = request.args.get('code')
        error = request.args.get('error')

        if error:
            logger.error(f"Spotify auth error: {error}")
            return render_template_string(SETUP_TEMPLATE, authenticated=False, error=f"Spotify authorization denied: {error}")

        if not code:
            return render_template_string(SETUP_TEMPLATE, authenticated=False, error="No authorization code received")

        # Exchange code for tokens
        spotify = SpotifyClient()
        spotify.authenticate_with_code(code)

        logger.info("Spotify authentication successful via web setup")
        return render_template_string(SETUP_TEMPLATE, authenticated=True, error=None)

    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}", exc_info=True)
        return render_template_string(SETUP_TEMPLATE, authenticated=False, error=f"Authentication failed: {str(e)}")

def run_server(host='0.0.0.0', port=8080):
    """Run the Flask web server.

    Args:
        host: Host to bind to (default: 0.0.0.0 for App Platform)
        port: Port to listen on (default: 8080 for App Platform)
    """
    logger.info(f"Starting web server on {host}:{port}")
    app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    run_server()
