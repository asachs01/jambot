"""Shared pytest fixtures for Jambot tests."""
import os
import tempfile
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any

# Create temp directories for logs and data
_temp_dir = tempfile.mkdtemp(prefix='jambot_test_')
_log_dir = os.path.join(_temp_dir, 'logs')
_data_dir = os.path.join(_temp_dir, 'data')
os.makedirs(_log_dir, exist_ok=True)
os.makedirs(_data_dir, exist_ok=True)

# Set test environment before any imports
os.environ['DISCORD_BOT_TOKEN'] = 'test-token'
os.environ['SPOTIFY_CLIENT_ID'] = 'test-client-id'
os.environ['SPOTIFY_CLIENT_SECRET'] = 'test-client-secret'
os.environ['SPOTIFY_REDIRECT_URI'] = 'http://localhost:8080/callback'
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'
os.environ['LOG_FILE'] = os.path.join(_log_dir, 'jambot.log')
os.environ['DATABASE_PATH'] = os.path.join(_data_dir, 'jambot.db')


# --- Sample Data Fixtures ---

@pytest.fixture
def sample_setlist_message():
    """Sample setlist message in standard format."""
    return """Here's the setlist for the 7pm jam on January 15, 2024.

1. Will the Circle Be Unbroken (G)
2. Blue Moon of Kentucky (A)
3. Foggy Mountain Breakdown (G)
4. Man of Constant Sorrow (D)
5. Rocky Top (A)
"""


@pytest.fixture
def sample_setlist_message_curly_quotes():
    """Sample setlist message with curly quotes (Discord formatting)."""
    return """Here's the setlist for the 7pm jam on January 15, 2024.

1. Will the Circle Be Unbroken (G)
2. Blue Moon of Kentucky (A)
3. Foggy Mountain Breakdown (G)
"""


@pytest.fixture
def sample_setlist_message_no_keys():
    """Sample setlist message without keys."""
    return """Here's the setlist for the afternoon jam on December 25, 2023.

1. Amazing Grace
2. I'll Fly Away
3. Angel Band
"""


@pytest.fixture
def sample_spotify_track():
    """Sample Spotify track data."""
    return {
        'id': 'track123',
        'name': 'Will the Circle Be Unbroken',
        'artist': 'The Nitty Gritty Dirt Band',
        'album': 'Will the Circle Be Unbroken',
        'url': 'https://open.spotify.com/track/track123',
        'uri': 'spotify:track:track123',
    }


@pytest.fixture
def sample_spotify_search_response():
    """Sample Spotify API search response."""
    return {
        'tracks': {
            'items': [
                {
                    'id': 'track123',
                    'name': 'Will the Circle Be Unbroken',
                    'artists': [{'name': 'The Nitty Gritty Dirt Band'}],
                    'album': {'name': 'Will the Circle Be Unbroken'},
                    'external_urls': {'spotify': 'https://open.spotify.com/track/track123'},
                    'uri': 'spotify:track:track123',
                },
                {
                    'id': 'track456',
                    'name': 'Will the Circle Be Unbroken (Live)',
                    'artists': [{'name': 'Doc Watson'}],
                    'album': {'name': 'Live Album'},
                    'external_urls': {'spotify': 'https://open.spotify.com/track/track456'},
                    'uri': 'spotify:track:track456',
                },
            ]
        }
    }


@pytest.fixture
def sample_bot_configuration():
    """Sample bot configuration from database."""
    return {
        'guild_id': 123456789,
        'jam_leader_ids': [111111111, 222222222],
        'approver_ids': [333333333, 444444444],
        'channel_id': 555555555,
        'playlist_name_template': 'Jam Session {date}',
        'spotify_client_id': 'test-client-id',
        'spotify_client_secret': 'test-secret',
        'spotify_redirect_uri': 'http://localhost:8080/callback',
        'setlist_intro_pattern': None,
        'setlist_song_pattern': None,
    }


@pytest.fixture
def sample_workflow():
    """Sample approval workflow data."""
    return {
        'id': 1,
        'guild_id': 123456789,
        'summary_message_id': 999999999,
        'original_channel_id': 555555555,
        'original_message_id': 888888888,
        'song_matches': [
            {
                'number': 1,
                'title': 'Will the Circle Be Unbroken',
                'stored_version': None,
                'spotify_results': [
                    {
                        'id': 'track123',
                        'name': 'Will the Circle Be Unbroken',
                        'artist': 'The Nitty Gritty Dirt Band',
                        'album': 'WTCBU',
                        'url': 'https://open.spotify.com/track/track123',
                        'uri': 'spotify:track:track123',
                    }
                ],
            },
            {
                'number': 2,
                'title': 'Blue Moon of Kentucky',
                'stored_version': {
                    'id': 'track789',
                    'name': 'Blue Moon of Kentucky',
                    'artist': 'Bill Monroe',
                    'album': 'Best Of',
                    'url': 'https://open.spotify.com/track/track789',
                    'uri': 'spotify:track:track789',
                },
                'spotify_results': [],
            },
        ],
        'selections': {
            '2': {
                'id': 'track789',
                'name': 'Blue Moon of Kentucky',
                'artist': 'Bill Monroe',
                'album': 'Best Of',
                'url': 'https://open.spotify.com/track/track789',
                'uri': 'spotify:track:track789',
            }
        },
        'message_ids': [100000001, 100000002],
        'approver_ids': [333333333],
        'setlist_data': {
            'date': 'January 15, 2024',
            'time': '7pm',
            'songs': [
                {'number': 1, 'title': 'Will the Circle Be Unbroken'},
                {'number': 2, 'title': 'Blue Moon of Kentucky'},
            ],
        },
        'status': 'pending',
        'initiated_by': 111111111,
    }


# --- Mock Fixtures ---

@pytest.fixture
def mock_discord_user():
    """Mock Discord user object."""
    user = MagicMock()
    user.id = 123456789
    user.name = 'TestUser'
    user.mention = '<@123456789>'
    user.send = AsyncMock()
    user.create_dm = AsyncMock(return_value=MagicMock(send=AsyncMock()))
    return user


@pytest.fixture
def mock_discord_message(mock_discord_user):
    """Mock Discord message object."""
    message = MagicMock()
    message.id = 987654321
    message.author = mock_discord_user
    message.content = "Test message content"
    message.channel = MagicMock()
    message.channel.id = 555555555
    message.channel.send = AsyncMock()
    message.channel.history = MagicMock()
    message.guild = MagicMock()
    message.guild.id = 123456789
    message.guild.name = 'Test Guild'
    message.jump_url = 'https://discord.com/channels/123/456/789'
    message.reply = AsyncMock()
    message.add_reaction = AsyncMock()
    message.reference = None
    return message


@pytest.fixture
def mock_discord_interaction(mock_discord_user):
    """Mock Discord interaction for slash commands."""
    interaction = MagicMock()
    interaction.user = mock_discord_user
    interaction.guild = MagicMock()
    interaction.guild.id = 123456789
    interaction.guild.name = 'Test Guild'
    interaction.guild.fetch_member = AsyncMock(return_value=mock_discord_user)
    interaction.guild.get_channel = MagicMock(return_value=MagicMock())
    interaction.guild_id = 123456789
    interaction.channel = MagicMock()
    interaction.channel.id = 555555555
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.send_modal = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.fixture
def mock_database():
    """Mock Database instance."""
    db = MagicMock()

    # Configuration methods
    db.get_bot_configuration = MagicMock(return_value=None)
    db.save_bot_configuration = MagicMock()
    db.is_jam_leader = MagicMock(return_value=False)
    db.is_approver = MagicMock(return_value=False)
    db.get_approver_ids = MagicMock(return_value=[])
    db.is_spotify_authorized = MagicMock(return_value=False)
    db.get_setlist_patterns = MagicMock(return_value={'intro_pattern': None, 'song_pattern': None})
    db.update_setlist_patterns = MagicMock(return_value=True)

    # Song methods
    db.get_song_by_title = MagicMock(return_value=None)
    db.add_or_update_song = MagicMock(return_value=1)

    # Setlist methods
    db.create_setlist = MagicMock(return_value=1)
    db.update_setlist_playlist = MagicMock()
    db.add_setlist_song = MagicMock()
    db.get_setlist_by_date = MagicMock(return_value=None)
    db.get_setlist_songs = MagicMock(return_value=[])

    # Workflow methods
    db.save_workflow = MagicMock()
    db.get_workflow = MagicMock(return_value=None)
    db.get_all_active_workflows = MagicMock(return_value=[])
    db.update_workflow_selection = MagicMock()
    db.delete_workflow = MagicMock()
    db.get_workflows_for_user = MagicMock(return_value=[])
    db.get_most_recent_workflow_for_user = MagicMock(return_value=None)
    db.update_workflow_status = MagicMock()
    db.get_expired_workflows = MagicMock(return_value=[])
    db.get_workflow_by_id = MagicMock(return_value=None)

    # Feedback methods
    db.save_feedback = MagicMock(return_value=1)
    db.mark_feedback_notified = MagicMock()
    db.get_unnotified_feedback = MagicMock(return_value=[])
    db.track_usage_event = MagicMock()
    db.save_satisfaction_rating = MagicMock()

    # Connection context manager
    db.get_connection = MagicMock()

    return db


@pytest.fixture
def mock_spotify_client():
    """Mock SpotifyClient instance."""
    client = MagicMock()
    client.user_id = 'test_spotify_user'
    client.sp = MagicMock()
    client.credentials = {
        'client_id': 'test-client-id',
        'client_secret': 'test-secret',
        'redirect_uri': 'http://localhost:8080/callback',
    }

    # Search methods
    client.search_song = MagicMock(return_value=[])
    client.get_track_from_url = MagicMock(return_value=None)

    # Playlist methods
    client.create_playlist = MagicMock(return_value={
        'id': 'playlist123',
        'url': 'https://open.spotify.com/playlist/playlist123',
    })
    client.add_tracks_to_playlist = MagicMock()

    # Auth methods
    client.get_auth_url = MagicMock(return_value='https://accounts.spotify.com/authorize')
    client.authenticate_with_code = MagicMock()
    client.is_authenticated = MagicMock(return_value=True)

    return client


@pytest.fixture
def mock_openrouter_client():
    """Mock OpenRouterClient instance."""
    client = MagicMock()
    client.api_key = 'test-openrouter-key'
    client.base_url = 'https://openrouter.ai/api/v1'
    client.primary_model = 'deepseek/deepseek-chat:v3'
    client.fallback_model = 'meta-llama/llama-3.1-70b-instruct:free'
    client.current_model = 'deepseek/deepseek-chat:v3'
    client.max_retries = 3

    # Chat completion method
    client.chat_completion = AsyncMock(return_value={
        'content': 'Test response',
        'metadata': {
            'prompt_tokens': 10,
            'completion_tokens': 20,
            'latency_ms': 50.0,
            'cost_usd': 0.000007,
            'model_used': 'deepseek/deepseek-chat:v3',
        }
    })

    # Fallback method
    client._trigger_fallback = MagicMock()

    # Cost calculation method
    client._calculate_cost = MagicMock(return_value=0.000007)

    # Close method
    client.close = AsyncMock()

    return client


@pytest.fixture
def sample_openrouter_response():
    """Sample OpenRouter API response."""
    return {
        'content': 'This is a test response from OpenRouter.',
        'metadata': {
            'prompt_tokens': 10,
            'completion_tokens': 20,
            'latency_ms': 50.0,
            'cost_usd': 0.000007,
            'model_used': 'deepseek/deepseek-chat:v3',
        }
    }


# --- Database Test Fixtures ---

@pytest.fixture
def mock_pg_connection():
    """Mock PostgreSQL connection for database tests."""
    conn = MagicMock()
    cursor = MagicMock()

    # Setup cursor mock
    cursor.execute = MagicMock()
    cursor.fetchone = MagicMock(return_value=None)
    cursor.fetchall = MagicMock(return_value=[])

    # Cursor factory returns cursor
    conn.cursor = MagicMock(return_value=cursor)
    conn.commit = MagicMock()
    conn.rollback = MagicMock()
    conn.close = MagicMock()

    return conn, cursor


# --- Environment Cleanup ---

@pytest.fixture(autouse=True)
def clean_env():
    """Ensure test environment variables are set for each test."""
    # Set required environment variables for tests
    test_env = {
        'DISCORD_BOT_TOKEN': 'test-token',
        'SPOTIFY_CLIENT_ID': 'test-client-id',
        'SPOTIFY_CLIENT_SECRET': 'test-client-secret',
        'SPOTIFY_REDIRECT_URI': 'http://localhost:8080/callback',
        'LOG_FILE': os.path.join(_log_dir, 'jambot.log'),
        'DATABASE_PATH': os.path.join(_data_dir, 'jambot.db'),
    }

    for key, value in test_env.items():
        os.environ[key] = value

    yield
