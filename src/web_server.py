"""Web server for Jambot setup and Spotify authentication."""
from flask import Flask, redirect, request, render_template_string, url_for
from src.spotify_client import SpotifyClient
from src.database import Database
from src.config import Config
from src.logger import logger
import os
import base64
import json

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
    """Redirect to Spotify authorization (legacy single-guild)."""
    try:
        spotify = SpotifyClient()
        auth_url = spotify.get_auth_url()
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Error generating auth URL: {e}", exc_info=True)
        return render_template_string(SETUP_TEMPLATE, authenticated=False, error=f"Failed to generate auth URL: {str(e)}")

@app.route('/spotify/auth/<int:guild_id>/<int:user_id>')
def spotify_auth_guild(guild_id, user_id):
    """Initiate Spotify OAuth for a specific guild.

    Args:
        guild_id: Discord guild ID to associate Spotify auth with.
        user_id: Discord user ID who is authorizing.

    Returns:
        Redirect to Spotify authorization page with state parameter.
    """
    try:
        logger.info(f"Initiating Spotify auth for guild {guild_id} by user {user_id}")

        # Create state parameter with guild_id and user_id
        state_data = {
            'guild_id': guild_id,
            'user_id': user_id
        }
        state = base64.b64encode(json.dumps(state_data).encode('utf-8')).decode('utf-8')

        # Generate Spotify auth URL with state parameter
        spotify = SpotifyClient(guild_id=guild_id)
        auth_url = spotify.get_auth_url(state=state)

        return redirect(auth_url)

    except Exception as e:
        logger.error(f"Error generating auth URL for guild {guild_id}: {e}", exc_info=True)
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Error</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
                    .card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                    h1 { color: #e22134; margin-top: 0; }
                    .error { padding: 20px; border-radius: 8px; background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; margin: 20px 0; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>❌ Authentication Error</h1>
                    <div class="error">
                        Failed to start Spotify authentication.<br>
                        Error: {{ error }}
                    </div>
                    <p>Please try again or contact your server administrator.</p>
                </div>
            </body>
            </html>
        """, error=str(e))

@app.route('/callback')
def callback():
    """Handle Spotify OAuth callback - supports both old and new multi-guild flow."""
    try:
        code = request.args.get('code')
        error = request.args.get('error')
        state = request.args.get('state')

        if error:
            logger.error(f"Spotify auth error: {error}")
            return render_template_string(SETUP_TEMPLATE, authenticated=False, error=f"Spotify authorization denied: {error}")

        if not code:
            return render_template_string(SETUP_TEMPLATE, authenticated=False, error="No authorization code received")

        # Check if this is multi-guild auth (state parameter contains guild_id and user_id)
        if state:
            try:
                # Decode state parameter
                state_data = json.loads(base64.b64decode(state).decode('utf-8'))
                guild_id = state_data.get('guild_id')
                user_id = state_data.get('user_id')

                if guild_id and user_id:
                    # Multi-guild authentication flow
                    logger.info(f"Multi-guild Spotify auth for guild {guild_id} by user {user_id}")
                    spotify = SpotifyClient(guild_id=guild_id)
                    spotify.authenticate_with_code(code, user_id=user_id)

                    logger.info(f"Spotify authentication successful for guild {guild_id}")
                    return render_template_string("""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Spotify Connected!</title>
                            <style>
                                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
                                .card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
                                h1 { color: #1DB954; margin-top: 0; }
                                .status { padding: 20px; border-radius: 8px; background: #d4edda; color: #155724; border: 1px solid #c3e6cb; margin: 20px 0; }
                            </style>
                        </head>
                        <body>
                            <div class="card">
                                <h1>✅ Spotify Connected!</h1>
                                <div class="status">
                                    Your Discord server is now connected to Spotify.<br>
                                    Post a setlist in your Discord channel and JamBot will create a playlist!
                                </div>
                                <p>You can close this window and return to Discord.</p>
                            </div>
                        </body>
                        </html>
                    """)
            except Exception as decode_error:
                logger.error(f"Failed to decode state parameter: {decode_error}")
                # Fall through to legacy auth

        # Legacy single-guild authentication flow
        logger.warning("Using legacy single-guild Spotify auth (deprecated)")
        spotify = SpotifyClient()
        spotify.authenticate_with_code(code)

        logger.info("Spotify authentication successful via web setup (legacy)")
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
