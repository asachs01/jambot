"""Configuration management for Jambot."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Bot configuration from environment variables."""

    # Discord Configuration
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    DISCORD_JAM_LEADER_ID = os.getenv('DISCORD_JAM_LEADER_ID')
    DISCORD_ADMIN_ID = os.getenv('DISCORD_ADMIN_ID')

    # Spotify Configuration
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
    SPOTIFY_REFRESH_TOKEN = os.getenv('SPOTIFY_REFRESH_TOKEN')

    # Database Configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', '/app/data/jambot.db')

    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', '/app/logs/jambot.log')

    @classmethod
    def validate(cls):
        """Validate that all required configuration is present.

        Note: DISCORD_JAM_LEADER_ID and DISCORD_ADMIN_ID are optional as they
        can be configured via the /jambot-setup modal instead.

        SPOTIFY_REFRESH_TOKEN is also optional as tokens can be stored in the database.
        """
        required_vars = [
            'DISCORD_BOT_TOKEN',
            'SPOTIFY_CLIENT_ID',
            'SPOTIFY_CLIENT_SECRET',
            'SPOTIFY_REDIRECT_URI',
        ]

        missing = []
        for var in required_vars:
            if not getattr(cls, var):
                missing.append(var)

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return True
