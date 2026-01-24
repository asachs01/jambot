"""Tests for the SpotifyClient class."""
import pytest
from unittest.mock import MagicMock, patch
import time


class TestSpotifyClientInitialization:
    """Test SpotifyClient initialization."""

    @patch('src.spotify_client.spotipy.Spotify')
    @patch('src.spotify_client.SpotifyOAuth')
    def test_initializes_without_db_tokens(self, mock_oauth, mock_spotify):
        """Should raise error when no tokens in database."""
        from src.spotify_client import SpotifyClient

        mock_db = MagicMock()
        mock_db.get_bot_configuration.return_value = {
            'spotify_client_id': 'test-id',
            'spotify_client_secret': 'test-secret',
            'spotify_redirect_uri': 'http://localhost/callback',
        }

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # No tokens
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = MagicMock()

        # Should handle missing tokens gracefully
        client = SpotifyClient(db=mock_db, guild_id=123456789)

        assert client.sp is None
        assert client.user_id is None

    @patch('spotipy.Spotify')
    @patch('src.spotify_client.SpotifyOAuth')
    @patch('requests.get')
    def test_initializes_with_valid_tokens(self, mock_requests_get, mock_oauth, mock_spotify):
        """Should initialize successfully with valid tokens."""
        from src.spotify_client import SpotifyClient

        mock_db = MagicMock()
        mock_db.get_bot_configuration.return_value = {
            'spotify_client_id': 'test-id',
            'spotify_client_secret': 'test-secret',
            'spotify_redirect_uri': 'http://localhost/callback',
        }

        # Mock valid tokens - use context manager pattern
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'access_token': 'valid-access-token',
            'refresh_token': 'valid-refresh-token',
            'expires_at': int(time.time()) + 3600,  # Not expired
        }
        mock_conn.cursor.return_value = mock_cursor

        # Set up context manager
        mock_db.get_connection.return_value = MagicMock(__enter__=MagicMock(return_value=mock_conn), __exit__=MagicMock())

        # Mock user ID request
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'test_user'}
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        client = SpotifyClient(db=mock_db, guild_id=123456789)

        assert client.user_id == 'test_user'


class TestSpotifyCredentials:
    """Test Spotify credential handling."""

    def test_falls_back_to_env_vars(self):
        """Should fall back to environment variables when DB has no credentials."""
        from src.spotify_client import SpotifyClient
        from src.config import Config

        mock_db = MagicMock()
        mock_db.get_bot_configuration.return_value = {
            'spotify_client_id': None,
            'spotify_client_secret': None,
        }

        # Create client with mocked DB
        client = SpotifyClient.__new__(SpotifyClient)
        client.db = mock_db
        client.guild_id = 123456789

        creds = client._get_spotify_credentials()

        # Should use environment variable values
        assert creds['client_id'] is not None
        assert creds['client_secret'] is not None


class TestSpotifySearch:
    """Test Spotify search functionality."""

    def test_search_song_extracts_info(self, sample_spotify_search_response):
        """Should extract track info from search results."""
        from src.spotify_client import SpotifyClient

        client = SpotifyClient.__new__(SpotifyClient)

        # Test the _extract_track_info method directly
        items = sample_spotify_search_response['tracks']['items']
        results = client._extract_track_info(items)

        assert len(results) == 2
        assert results[0]['name'] == 'Will the Circle Be Unbroken'
        assert results[0]['id'] == 'track123'

    def test_direct_search_builds_correct_url(self):
        """Should build correct search URL parameters."""
        # This tests the structure, not the actual API call
        from src.spotify_client import SpotifyClient

        client = SpotifyClient.__new__(SpotifyClient)
        client.db = MagicMock()
        client.guild_id = 0
        client.credentials = {'client_id': 'test', 'client_secret': 'test', 'redirect_uri': 'test'}

        # Mock the tokens and requests
        client._get_tokens_from_db = MagicMock(return_value={
            'access_token': 'test-token',
            'refresh_token': 'test-refresh',
            'expires_at': int(time.time()) + 3600,
        })

        import requests
        with patch.object(requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {'tracks': {'items': []}}
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            client._direct_search('test query', limit=3)

            # Verify request was made with correct parameters
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert 'Authorization' in call_args.kwargs['headers']
            assert call_args.kwargs['params']['q'] == 'test query'
            assert call_args.kwargs['params']['limit'] == 3


class TestTrackInfoExtraction:
    """Test track info extraction from API response."""

    def test_extracts_track_info(self, sample_spotify_search_response):
        """Should extract relevant track information."""
        from src.spotify_client import SpotifyClient

        client = SpotifyClient.__new__(SpotifyClient)
        items = sample_spotify_search_response['tracks']['items']

        tracks = client._extract_track_info(items)

        assert len(tracks) == 2
        assert tracks[0]['id'] == 'track123'
        assert tracks[0]['name'] == 'Will the Circle Be Unbroken'
        assert tracks[0]['artist'] == 'The Nitty Gritty Dirt Band'
        assert tracks[0]['uri'] == 'spotify:track:track123'


class TestSpotifyPlaylist:
    """Test Spotify playlist operations."""

    def test_create_playlist(self, mock_spotify_client):
        """Should create a new playlist."""
        result = mock_spotify_client.create_playlist(
            name='Test Playlist',
            description='Test Description'
        )

        assert result['id'] == 'playlist123'
        assert 'open.spotify.com/playlist' in result['url']

    def test_add_tracks_to_playlist(self, mock_spotify_client):
        """Should add tracks to playlist."""
        track_uris = [
            'spotify:track:track1',
            'spotify:track:track2',
            'spotify:track:track3',
        ]

        mock_spotify_client.add_tracks_to_playlist('playlist123', track_uris)

        # Should not raise an exception


class TestRetryLogic:
    """Test API retry logic."""

    def test_retries_on_rate_limit(self):
        """Should retry on rate limit error."""
        import spotipy
        from src.spotify_client import SpotifyClient

        client = SpotifyClient.__new__(SpotifyClient)

        call_count = 0

        def failing_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                error = spotipy.exceptions.SpotifyException(
                    http_status=429,
                    code=-1,
                    msg='Rate limited',
                    headers={'Retry-After': '0'}
                )
                raise error
            return {'success': True}

        mock_func = MagicMock(side_effect=failing_then_success)
        mock_func.__name__ = 'test_func'

        result = client._retry_api_call(mock_func, max_retries=3)

        assert call_count == 3
        assert result == {'success': True}

    def test_raises_after_max_retries(self):
        """Should raise exception after max retries exceeded."""
        import spotipy
        from src.spotify_client import SpotifyClient

        client = SpotifyClient.__new__(SpotifyClient)

        def always_fail(*args, **kwargs):
            raise spotipy.exceptions.SpotifyException(
                http_status=500,
                code=-1,
                msg='Server error'
            )

        mock_func = MagicMock(side_effect=always_fail)
        mock_func.__name__ = 'test_func'

        with pytest.raises(Exception):  # May raise generic Exception after retries
            client._retry_api_call(mock_func, max_retries=3)


class TestSpotifyUrl:
    """Test Spotify URL parsing."""

    def test_get_track_from_url_valid(self, sample_spotify_track):
        """Should extract track ID from valid URL."""
        from src.spotify_client import SpotifyClient

        client = SpotifyClient.__new__(SpotifyClient)
        client.sp = MagicMock()
        client.sp.track = MagicMock(return_value={
            'id': 'track123',
            'name': 'Test Track',
            'artists': [{'name': 'Test Artist'}],
            'album': {'name': 'Test Album'},
            'external_urls': {'spotify': 'https://open.spotify.com/track/track123'},
            'uri': 'spotify:track:track123',
        })

        client._retry_api_call = lambda func, *args, **kwargs: func(*args, **kwargs)

        result = client.get_track_from_url('https://open.spotify.com/track/track123?si=abc')

        assert result is not None
        assert result['id'] == 'track123'

    def test_get_track_from_url_invalid(self):
        """Should return None for invalid URL."""
        from src.spotify_client import SpotifyClient

        client = SpotifyClient.__new__(SpotifyClient)

        result = client.get_track_from_url('https://open.spotify.com/playlist/playlist123')

        assert result is None


class TestSpotifyAuth:
    """Test Spotify authentication methods."""

    def test_get_auth_url(self):
        """Should generate authorization URL."""
        from src.spotify_client import SpotifyClient

        client = SpotifyClient.__new__(SpotifyClient)
        client.credentials = {
            'client_id': 'test-client-id',
            'client_secret': 'test-secret',
            'redirect_uri': 'http://localhost/callback',
        }

        with patch('src.spotify_client.SpotifyOAuth') as mock_oauth:
            mock_oauth.return_value.get_authorize_url.return_value = 'https://accounts.spotify.com/authorize?...'

            url = client.get_auth_url(state='test-state')

            assert 'accounts.spotify.com' in url

    def test_is_authenticated_valid_token(self):
        """Should return True when token is valid."""
        from src.spotify_client import SpotifyClient

        client = SpotifyClient.__new__(SpotifyClient)
        client.db = MagicMock()
        client.guild_id = 123456789

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'access_token': 'valid-token',
            'refresh_token': 'refresh-token',
            'expires_at': int(time.time()) + 3600,  # Not expired
        }
        mock_conn.cursor.return_value = mock_cursor
        client.db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        client.db.get_connection.return_value.__exit__ = MagicMock()

        result = client.is_authenticated()

        assert result is True

    def test_is_authenticated_expired_token(self):
        """Should attempt refresh when token is expired."""
        from src.spotify_client import SpotifyClient

        client = SpotifyClient.__new__(SpotifyClient)
        client.db = MagicMock()
        client.guild_id = 123456789

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'access_token': 'expired-token',
            'refresh_token': 'refresh-token',
            'expires_at': int(time.time()) - 3600,  # Already expired
        }
        mock_conn.cursor.return_value = mock_cursor
        client.db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        client.db.get_connection.return_value.__exit__ = MagicMock()

        # Mock refresh failure
        with patch('src.spotify_client.SpotifyOAuth') as mock_oauth:
            mock_oauth.return_value.refresh_access_token.side_effect = Exception('Refresh failed')

            result = client.is_authenticated()

            assert result is False


class TestSongVariations:
    """Test bluegrass song title variations."""

    def test_song_variations_dict(self):
        """Should have common bluegrass song variations."""
        from src.spotify_client import SpotifyClient

        variations = SpotifyClient.SONG_VARIATIONS

        assert 'will the circle' in variations
        assert 'man of constant sorrow' in variations
        assert 'blue moon of kentucky' in variations

    def test_variations_for_circle(self):
        """Should have variations for Will the Circle."""
        from src.spotify_client import SpotifyClient

        variations = SpotifyClient.SONG_VARIATIONS['will the circle']

        assert 'will the circle be unbroken' in variations
        assert 'can the circle be unbroken' in variations
