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
    # PostgreSQL connection URL (preferred for production)
    # Format: postgresql://user:password@host:port/database?sslmode=require
    # Can also be built from individual PG* environment variables
    @staticmethod
    def _build_database_url():
        """Build DATABASE_URL from environment variables."""
        # First check for explicit DATABASE_URL
        url = os.getenv('DATABASE_URL')
        if url:
            return url

        # Build from individual PG* variables
        user = os.getenv('PGUSER')
        password = os.getenv('PGPASS')
        host = os.getenv('PGHOST')
        port = os.getenv('PGPORT', '25060')
        database = os.getenv('PGDATABASE', 'defaultdb')
        sslmode = os.getenv('PGSSLMODE', 'require')

        if user and password and host:
            return f'postgresql://{user}:{password}@{host}:{port}/{database}?sslmode={sslmode}'

        return None

    DATABASE_URL = _build_database_url.__func__()

    # Legacy SQLite path (no longer used - PostgreSQL required)
    DATABASE_PATH = os.getenv('DATABASE_PATH', '/app/data/jambot.db')

    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', '/app/logs/jambot.log')

    # Feedback Configuration
    # Discord user ID to receive feedback notifications via DM
    FEEDBACK_NOTIFY_USER_ID = os.getenv('FEEDBACK_NOTIFY_USER_ID')

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
