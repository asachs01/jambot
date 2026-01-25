"""Tests for the Database class."""
import json
import pytest
from unittest.mock import MagicMock, patch, call
from contextlib import contextmanager


class TestDatabaseConfiguration:
    """Test database bot configuration methods."""

    @patch('src.database.psycopg2.connect')
    def test_save_and_get_configuration(self, mock_connect, sample_bot_configuration):
        """Should save and retrieve bot configuration."""
        # Setup mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Mock cursor for get operation
        mock_cursor.fetchone.return_value = {
            'guild_id': sample_bot_configuration['guild_id'],
            'jam_leader_ids': json.dumps(sample_bot_configuration['jam_leader_ids']),
            'approver_ids': json.dumps(sample_bot_configuration['approver_ids']),
            'channel_id': sample_bot_configuration['channel_id'],
            'playlist_name_template': sample_bot_configuration['playlist_name_template'],
            'spotify_client_id': sample_bot_configuration['spotify_client_id'],
            'spotify_client_secret': sample_bot_configuration['spotify_client_secret'],
            'spotify_redirect_uri': sample_bot_configuration['spotify_redirect_uri'],
            'setlist_intro_pattern': None,
            'setlist_song_pattern': None,
        }

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        # Save configuration
        db.save_bot_configuration(
            guild_id=sample_bot_configuration['guild_id'],
            jam_leader_ids=sample_bot_configuration['jam_leader_ids'],
            approver_ids=sample_bot_configuration['approver_ids'],
            channel_id=sample_bot_configuration['channel_id'],
            playlist_name_template=sample_bot_configuration['playlist_name_template'],
            spotify_client_id=sample_bot_configuration['spotify_client_id'],
            spotify_client_secret=sample_bot_configuration['spotify_client_secret'],
            updated_by=111111111
        )

        # Verify save was called with expected data
        save_call = mock_cursor.execute.call_args_list[-1]
        assert 'INSERT INTO bot_configuration' in save_call[0][0]

        # Get configuration
        config = db.get_bot_configuration(sample_bot_configuration['guild_id'])

        assert config is not None
        assert config['guild_id'] == sample_bot_configuration['guild_id']
        assert config['jam_leader_ids'] == sample_bot_configuration['jam_leader_ids']
        assert config['approver_ids'] == sample_bot_configuration['approver_ids']

    @patch('src.database.psycopg2.connect')
    def test_is_jam_leader(self, mock_connect, sample_bot_configuration):
        """Should correctly identify jam leaders."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.fetchone.return_value = {
            'guild_id': sample_bot_configuration['guild_id'],
            'jam_leader_ids': json.dumps(sample_bot_configuration['jam_leader_ids']),
            'approver_ids': json.dumps(sample_bot_configuration['approver_ids']),
            'channel_id': sample_bot_configuration['channel_id'],
            'playlist_name_template': sample_bot_configuration['playlist_name_template'],
        }

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        # Test jam leader
        assert db.is_jam_leader(sample_bot_configuration['guild_id'], 111111111) is True
        assert db.is_jam_leader(sample_bot_configuration['guild_id'], 999999999) is False

    @patch('src.database.psycopg2.connect')
    def test_is_approver(self, mock_connect, sample_bot_configuration):
        """Should correctly identify approvers."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.fetchone.return_value = {
            'guild_id': sample_bot_configuration['guild_id'],
            'jam_leader_ids': json.dumps(sample_bot_configuration['jam_leader_ids']),
            'approver_ids': json.dumps(sample_bot_configuration['approver_ids']),
            'channel_id': None,
            'playlist_name_template': None,
        }

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        assert db.is_approver(sample_bot_configuration['guild_id'], 333333333) is True
        assert db.is_approver(sample_bot_configuration['guild_id'], 999999999) is False

    @patch('src.database.psycopg2.connect')
    def test_get_approver_ids(self, mock_connect, sample_bot_configuration):
        """Should return list of approver IDs."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.fetchone.return_value = {
            'guild_id': sample_bot_configuration['guild_id'],
            'jam_leader_ids': json.dumps(sample_bot_configuration['jam_leader_ids']),
            'approver_ids': json.dumps(sample_bot_configuration['approver_ids']),
            'channel_id': None,
            'playlist_name_template': None,
        }

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        approvers = db.get_approver_ids(sample_bot_configuration['guild_id'])
        assert approvers == sample_bot_configuration['approver_ids']

    @patch('src.database.psycopg2.connect')
    def test_get_approver_ids_no_config(self, mock_connect):
        """Should return empty list when no config exists."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = None

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        approvers = db.get_approver_ids(123456789)
        assert approvers == []


class TestDatabaseSongs:
    """Test database song methods."""

    @patch('src.database.psycopg2.connect')
    def test_get_song_by_title_found(self, mock_connect):
        """Should return song when found in database."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.fetchone.return_value = {
            'id': 1,
            'guild_id': 123456789,
            'song_title': 'Will the Circle Be Unbroken',
            'spotify_track_id': 'track123',
            'spotify_track_name': 'Will the Circle Be Unbroken',
            'artist': 'The Nitty Gritty Dirt Band',
            'album': 'Will the Circle Be Unbroken',
            'spotify_url': 'https://open.spotify.com/track/track123',
        }

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        result = db.get_song_by_title(123456789, 'Will the Circle Be Unbroken')

        assert result is not None
        assert result['song_title'] == 'Will the Circle Be Unbroken'
        assert result['spotify_track_id'] == 'track123'

    @patch('src.database.psycopg2.connect')
    def test_get_song_by_title_not_found(self, mock_connect):
        """Should return None when song not found."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = None

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        result = db.get_song_by_title(123456789, 'Unknown Song')
        assert result is None

    @patch('src.database.psycopg2.connect')
    def test_add_or_update_song(self, mock_connect, sample_spotify_track):
        """Should insert or update song in database."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = (1,)  # Return song ID

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        song_id = db.add_or_update_song(
            guild_id=123456789,
            song_title='Will the Circle Be Unbroken',
            spotify_track_id=sample_spotify_track['id'],
            spotify_track_name=sample_spotify_track['name'],
            artist=sample_spotify_track['artist'],
            album=sample_spotify_track['album'],
            spotify_url=sample_spotify_track['url']
        )

        assert song_id == 1

        # Verify upsert SQL was used
        call_args = mock_cursor.execute.call_args_list[-1]
        assert 'INSERT INTO songs' in call_args[0][0]
        assert 'ON CONFLICT' in call_args[0][0]


class TestDatabaseSetlists:
    """Test database setlist methods."""

    @patch('src.database.psycopg2.connect')
    def test_create_setlist(self, mock_connect):
        """Should create a new setlist."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = (1,)

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        setlist_id = db.create_setlist(
            guild_id=123456789,
            date='January 15, 2024',
            time='7pm',
            playlist_name='Bluegrass Jam January 15, 2024'
        )

        assert setlist_id == 1

    @patch('src.database.psycopg2.connect')
    def test_update_setlist_playlist(self, mock_connect):
        """Should update setlist with Spotify playlist info."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        db.update_setlist_playlist(
            setlist_id=1,
            playlist_id='playlist123',
            playlist_url='https://open.spotify.com/playlist/playlist123'
        )

        # Verify update was called
        call_args = mock_cursor.execute.call_args_list[-1]
        assert 'UPDATE setlists' in call_args[0][0]


class TestDatabaseWorkflows:
    """Test database workflow methods."""

    @patch('src.database.psycopg2.connect')
    def test_save_workflow(self, mock_connect, sample_workflow):
        """Should save workflow to database."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        db.save_workflow(sample_workflow, sample_workflow['summary_message_id'])

        # Verify insert was called
        call_args = mock_cursor.execute.call_args_list[-1]
        assert 'INSERT INTO active_workflows' in call_args[0][0]

    @patch('src.database.psycopg2.connect')
    def test_get_workflow(self, mock_connect, sample_workflow):
        """Should retrieve workflow from database."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.fetchone.return_value = (
            sample_workflow['guild_id'],
            sample_workflow['summary_message_id'],
            sample_workflow['original_channel_id'],
            sample_workflow['original_message_id'],
            sample_workflow['song_matches'],  # JSONB auto-parsed
            sample_workflow['selections'],
            sample_workflow['message_ids'],
            sample_workflow['approver_ids'],
            sample_workflow['setlist_data'],
        )

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        result = db.get_workflow(sample_workflow['summary_message_id'])

        assert result is not None
        assert result['guild_id'] == sample_workflow['guild_id']
        assert result['summary_message_id'] == sample_workflow['summary_message_id']

    @patch('src.database.psycopg2.connect')
    def test_update_workflow_selection(self, mock_connect, sample_spotify_track):
        """Should update single song selection in workflow."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        db.update_workflow_selection(
            summary_message_id=999999999,
            song_number=1,
            track=sample_spotify_track
        )

        # Verify jsonb_set was used for atomic update
        call_args = mock_cursor.execute.call_args_list[-1]
        assert 'jsonb_set' in call_args[0][0]

    @patch('src.database.psycopg2.connect')
    def test_delete_workflow(self, mock_connect):
        """Should delete workflow from database."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        db.delete_workflow(999999999)

        call_args = mock_cursor.execute.call_args_list[-1]
        assert 'DELETE FROM active_workflows' in call_args[0][0]


class TestDatabaseFeedback:
    """Test database feedback methods."""

    @patch('src.database.psycopg2.connect')
    def test_save_feedback(self, mock_connect):
        """Should save user feedback to database."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = (1,)

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        feedback_id = db.save_feedback(
            guild_id=123456789,
            user_id=111111111,
            feedback_type='bug',
            message='Something is broken',
            context='Tried to create playlist'
        )

        assert feedback_id == 1

    @patch('src.database.psycopg2.connect')
    def test_track_usage_event(self, mock_connect):
        """Should track usage events with upsert."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        db.track_usage_event(
            guild_id=123456789,
            event_type='playlist_created',
            event_data={'song_count': 5}
        )

        # Verify upsert with count increment
        call_args = mock_cursor.execute.call_args_list[-1]
        assert 'INSERT INTO usage_stats' in call_args[0][0]
        assert 'ON CONFLICT' in call_args[0][0]


class TestDatabasePatterns:
    """Test database setlist pattern methods."""

    @patch('src.database.psycopg2.connect')
    def test_get_setlist_patterns(self, mock_connect, sample_bot_configuration):
        """Should retrieve setlist patterns from config."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_cursor.fetchone.return_value = {
            'guild_id': sample_bot_configuration['guild_id'],
            'jam_leader_ids': json.dumps(sample_bot_configuration['jam_leader_ids']),
            'approver_ids': json.dumps(sample_bot_configuration['approver_ids']),
            'channel_id': sample_bot_configuration['channel_id'],
            'playlist_name_template': sample_bot_configuration['playlist_name_template'],
            'setlist_intro_pattern': r'custom intro (.+?) and (.+?)\.',
            'setlist_song_pattern': r'^\d+\.\s+(.+)$',
        }

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        patterns = db.get_setlist_patterns(sample_bot_configuration['guild_id'])

        assert patterns['intro_pattern'] == r'custom intro (.+?) and (.+?)\.'
        assert patterns['song_pattern'] == r'^\d+\.\s+(.+)$'

    @patch('src.database.psycopg2.connect')
    def test_update_setlist_patterns(self, mock_connect, sample_bot_configuration):
        """Should update setlist patterns in config."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # First call returns existing config, subsequent calls for update
        mock_cursor.fetchone.return_value = {
            'guild_id': sample_bot_configuration['guild_id'],
            'jam_leader_ids': json.dumps(sample_bot_configuration['jam_leader_ids']),
            'approver_ids': json.dumps(sample_bot_configuration['approver_ids']),
            'channel_id': None,
            'playlist_name_template': None,
            'setlist_intro_pattern': None,
            'setlist_song_pattern': None,
        }

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        result = db.update_setlist_patterns(
            guild_id=sample_bot_configuration['guild_id'],
            setlist_intro_pattern=r'new pattern (.+?)',
            updated_by=111111111
        )

        assert result is True

class TestChordChartLLMFeatures:
    """Test LLM-related chord chart database methods."""

    @patch('src.database.psycopg2.connect')
    def test_create_chord_chart_with_llm_fields(self, mock_connect):
        """Test creating chord chart with LLM-specific fields."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = (1,)

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        chart_id = db.create_chord_chart(
            guild_id=12345,
            title="Mountain Dew",
            keys=[{'key': 'G', 'sections': [{'label': 'Verse', 'chords': ['G', 'C', 'D', 'G']}]}],
            created_by=67890,
            source='ai_generated',
            status='draft',
            alternate_titles=['Mtn Dew', 'Mountain Due'],
        )

        assert chart_id == 1
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args[0]
        assert 'source' in call_args[0]
        assert 'status' in call_args[0]
        assert 'alternate_titles' in call_args[0]

    @patch('src.database.psycopg2.connect')
    def test_fuzzy_search_chord_chart_finds_match(self, mock_connect):
        """Test fuzzy_search_chord_chart finds similar title."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Mock return value for fuzzy search
        mock_cursor.fetchone.return_value = {
            'id': 1,
            'guild_id': 12345,
            'title': 'Will the Circle Be Unbroken',
            'keys': [{'key': 'G', 'sections': []}],
            'status': 'approved',
            'source': 'user_created',
        }

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        result = db.fuzzy_search_chord_chart(12345, 'Circle Be Unbroken')

        assert result is not None
        assert result['title'] == 'Will the Circle Be Unbroken'
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args[0]
        # Verify pg_trgm similarity operator used
        assert '%%' in call_args[0]

    @patch('src.database.psycopg2.connect')
    def test_fuzzy_search_chord_chart_no_match(self, mock_connect):
        """Test fuzzy_search_chord_chart returns None when no match."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = None

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        result = db.fuzzy_search_chord_chart(12345, 'Nonexistent Song')

        assert result is None

    @patch('src.database.psycopg2.connect')
    def test_create_generation_history(self, mock_connect):
        """Test create_generation_history stores LLM generation record."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = (1,)

        from src.database import Database
        db = Database(database_url='postgresql://test:test@localhost/test')

        history_id = db.create_generation_history(
            chart_id=1,
            prompt="Generate chord chart for 'Mountain Dew'",
            response={
                'title': 'Mountain Dew',
                'key': 'G',
                'sections': [{'label': 'Verse', 'chords': ['G', 'C', 'D', 'G']}]
            },
            model='gpt-4'
        )

        assert history_id == 1
        mock_cursor.execute.assert_called()
        call_args = mock_cursor.execute.call_args[0]
        assert 'generation_history' in call_args[0]
        assert 'prompt' in call_args[0]
        assert 'response' in call_args[0]
        assert 'model' in call_args[0]
