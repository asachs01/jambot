"""Tests for the JamBot class."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
import discord


class TestJamBotInitialization:
    """Test JamBot initialization."""

    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    def test_initializes_components(self, mock_parser, mock_commands, mock_db):
        """Should initialize all required components."""
        from src.bot import JamBot

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            assert bot.db is not None
            assert bot.commands_handler is not None
            assert bot.active_workflows == {}
            mock_task.start.assert_called_once()


class TestWorkflowReadiness:
    """Test workflow readiness checking."""

    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    def test_is_workflow_ready_complete(self, mock_parser, mock_commands, mock_db, sample_workflow):
        """Should return True when all songs have selections."""
        from src.bot import JamBot

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            # Add selection for song 1 (song 2 already has selection)
            sample_workflow['selections']['1'] = sample_workflow['song_matches'][0]['spotify_results'][0]

            is_ready, missing = bot.is_workflow_ready(sample_workflow)

            assert is_ready is True
            assert missing == []

    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    def test_is_workflow_ready_incomplete(self, mock_parser, mock_commands, mock_db, sample_workflow):
        """Should return False with missing songs when incomplete."""
        from src.bot import JamBot

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            # Only song 2 has selection (from stored_version)
            is_ready, missing = bot.is_workflow_ready(sample_workflow)

            assert is_ready is False
            assert 'Will the Circle Be Unbroken' in missing


class TestParserCaching:
    """Test guild-specific parser caching."""

    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    def test_get_parser_for_guild_default(self, mock_parser_class, mock_commands, mock_db):
        """Should return default parser when no custom patterns configured."""
        from src.bot import JamBot

        mock_db_instance = MagicMock()
        mock_db_instance.get_setlist_patterns.return_value = {
            'intro_pattern': None,
            'song_pattern': None
        }
        mock_db.return_value = mock_db_instance

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            parser = bot.get_parser_for_guild(123456789)

            assert parser == bot._default_parser

    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    def test_get_parser_for_guild_custom(self, mock_parser_class, mock_commands, mock_db):
        """Should create custom parser when patterns configured."""
        from src.bot import JamBot

        mock_db_instance = MagicMock()
        mock_db_instance.get_setlist_patterns.return_value = {
            'intro_pattern': r'Custom pattern (.+)',
            'song_pattern': None
        }
        mock_db.return_value = mock_db_instance

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            parser = bot.get_parser_for_guild(123456789)

            # Should not be the default parser
            assert 123456789 in bot._guild_parsers

    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    def test_invalidate_parser_cache(self, mock_parser_class, mock_commands, mock_db):
        """Should remove parser from cache when invalidated."""
        from src.bot import JamBot

        mock_db_instance = MagicMock()
        mock_db_instance.get_setlist_patterns.return_value = {
            'intro_pattern': r'Custom pattern (.+)',
            'song_pattern': None
        }
        mock_db.return_value = mock_db_instance

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            # Get parser to add to cache
            bot.get_parser_for_guild(123456789)
            assert 123456789 in bot._guild_parsers

            # Invalidate cache
            bot.invalidate_parser_cache(123456789)
            assert 123456789 not in bot._guild_parsers


class TestWorkflowCleanup:
    """Test workflow cleanup functionality."""

    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    def test_cleanup_workflow(self, mock_parser, mock_commands, mock_db, sample_workflow):
        """Should clean up workflow from active_workflows and database."""
        from src.bot import JamBot

        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            # Add workflow to active_workflows
            for msg_id in sample_workflow['message_ids'] + [sample_workflow['summary_message_id']]:
                bot.active_workflows[msg_id] = sample_workflow

            bot.cleanup_workflow(sample_workflow)

            # All message IDs should be removed
            for msg_id in sample_workflow['message_ids'] + [sample_workflow['summary_message_id']]:
                assert msg_id not in bot.active_workflows

            # Database delete should be called
            mock_db_instance.delete_workflow.assert_called_once_with(
                sample_workflow['summary_message_id']
            )


class TestMessageHandling:
    """Test message handling."""

    @pytest.mark.asyncio
    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    async def test_ignores_own_messages(self, mock_parser, mock_commands, mock_db, mock_discord_message):
        """Should ignore bot's own messages."""
        from src.bot import JamBot

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            # Mock the user property
            with patch.object(type(bot), 'user', new_callable=lambda: property(lambda self: MagicMock(id=mock_discord_message.author.id))):
                # This should not raise or do anything
                await bot.on_message(mock_discord_message)

    @pytest.mark.asyncio
    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    async def test_detects_setlist_from_jam_leader(
        self, mock_parser_class, mock_commands, mock_db,
        mock_discord_message, sample_setlist_message
    ):
        """Should detect and process setlist from jam leader."""
        from src.bot import JamBot

        mock_db_instance = MagicMock()
        mock_db_instance.is_jam_leader.return_value = True
        mock_db_instance.get_setlist_patterns.return_value = {
            'intro_pattern': None,
            'song_pattern': None
        }
        mock_db_instance.get_approver_ids.return_value = []
        mock_db.return_value = mock_db_instance

        mock_parser_instance = MagicMock()
        mock_parser_instance.is_setlist_message.return_value = True
        mock_parser_instance.parse_setlist.return_value = {
            'date': 'January 15, 2024',
            'time': '7pm',
            'songs': [{'number': 1, 'title': 'Test Song'}],
        }
        mock_parser_class.return_value = mock_parser_instance

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            bot._default_parser = mock_parser_instance
            bot.process_commands = AsyncMock()
            bot.handle_setlist_message = AsyncMock()

            mock_discord_message.content = sample_setlist_message

            # Mock the user property with a different ID
            mock_user = MagicMock()
            mock_user.id = 999999999
            with patch.object(type(bot), 'user', new_callable=lambda: property(lambda self: mock_user)):
                await bot.on_message(mock_discord_message)

                bot.handle_setlist_message.assert_called_once_with(mock_discord_message)


class TestDMHandling:
    """Test DM message handling for manual song selection."""

    @pytest.mark.asyncio
    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    @patch('src.bot.SpotifyClient')
    async def test_handles_manual_spotify_url(
        self, mock_spotify_class, mock_parser, mock_commands, mock_db,
        mock_discord_message, sample_spotify_track, sample_workflow
    ):
        """Should handle manual Spotify URL submissions via DM."""
        from src.bot import JamBot

        mock_db_instance = MagicMock()
        mock_db_instance.add_or_update_song.return_value = 1
        mock_db.return_value = mock_db_instance

        mock_spotify_instance = MagicMock()
        mock_spotify_instance.get_track_from_url.return_value = sample_spotify_track
        mock_spotify_class.return_value = mock_spotify_instance

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            # Set up message as DM reply
            mock_discord_message.guild = None  # DM has no guild
            mock_discord_message.reference = MagicMock()
            mock_discord_message.reference.message_id = sample_workflow['message_ids'][0]
            mock_discord_message.content = 'https://open.spotify.com/track/abc123'
            mock_discord_message.reply = AsyncMock()

            # Add workflow to active_workflows
            for msg_id in sample_workflow['message_ids']:
                bot.active_workflows[msg_id] = sample_workflow

            # Mock the user property
            mock_user = MagicMock()
            mock_user.id = 999999999
            with patch.object(type(bot), 'user', new_callable=lambda: property(lambda self: mock_user)):
                await bot.handle_dm_message(mock_discord_message)

                # Should confirm selection
                mock_discord_message.reply.assert_called()
                call_args = mock_discord_message.reply.call_args
                assert 'Manual selection confirmed' in str(call_args)


class TestEmojiConstants:
    """Test emoji constants are correct."""

    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    def test_emoji_constants(self, mock_parser, mock_commands, mock_db):
        """Should have correct emoji constants."""
        from src.bot import JamBot

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            assert bot.APPROVE_EMOJI == "✅"
            assert bot.REJECT_EMOJI == "❌"
            assert bot.SELECT_EMOJIS == ["1️⃣", "2️⃣", "3️⃣"]


class TestSongApprovalEmbed:
    """Test song approval embed creation."""

    @pytest.mark.asyncio
    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    async def test_embed_for_stored_version(self, mock_parser, mock_commands, mock_db):
        """Should create green embed for stored version."""
        from src.bot import JamBot

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            match = {
                'number': 1,
                'title': 'Test Song',
                'stored_version': {
                    'name': 'Test Song',
                    'artist': 'Test Artist',
                    'album': 'Test Album',
                    'url': 'https://open.spotify.com/track/test',
                },
                'spotify_results': [],
            }

            embed = await bot.create_song_approval_embed(match)

            assert embed.color == discord.Color.green()
            assert 'Stored Version' in embed.description

    @pytest.mark.asyncio
    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    async def test_embed_for_no_matches(self, mock_parser, mock_commands, mock_db):
        """Should create red embed when no matches found."""
        from src.bot import JamBot

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            match = {
                'number': 1,
                'title': 'Obscure Song',
                'stored_version': None,
                'spotify_results': [],
            }

            embed = await bot.create_song_approval_embed(match)

            assert embed.color == discord.Color.red()
            assert 'No matches found' in embed.description

    @pytest.mark.asyncio
    @patch('src.bot.Database')
    @patch('src.bot.JambotCommands')
    @patch('src.bot.SetlistParser')
    async def test_embed_for_multiple_matches(self, mock_parser, mock_commands, mock_db):
        """Should create gold embed with options for multiple matches."""
        from src.bot import JamBot

        with patch.object(JamBot, 'cleanup_expired_workflows') as mock_task:
            mock_task.start = MagicMock()
            bot = JamBot()

            match = {
                'number': 1,
                'title': 'Test Song',
                'stored_version': None,
                'spotify_results': [
                    {'name': 'Version 1', 'artist': 'Artist 1', 'album': 'Album 1', 'url': 'url1'},
                    {'name': 'Version 2', 'artist': 'Artist 2', 'album': 'Album 2', 'url': 'url2'},
                    {'name': 'Version 3', 'artist': 'Artist 3', 'album': 'Album 3', 'url': 'url3'},
                ],
            }

            embed = await bot.create_song_approval_embed(match)

            assert embed.color == discord.Color.gold()
            assert '3 matches found' in embed.description
            assert len(embed.fields) == 3  # One field per option
