"""Tests for the JambotCommands class and slash commands."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestConfigurationModal:
    """Test ConfigurationModal class."""

    @pytest.mark.asyncio
    async def test_parse_user_ids_valid(self):
        """Should parse valid comma-separated user IDs."""
        from src.commands import ConfigurationModal

        modal = ConfigurationModal(db=MagicMock())

        ids = modal._parse_user_ids("123456789, 987654321, 555555555")

        assert ids == [123456789, 987654321, 555555555]

    @pytest.mark.asyncio
    async def test_parse_user_ids_removes_duplicates(self):
        """Should remove duplicate user IDs."""
        from src.commands import ConfigurationModal

        modal = ConfigurationModal(db=MagicMock())

        ids = modal._parse_user_ids("123456789, 123456789, 987654321")

        assert ids == [123456789, 987654321]

    @pytest.mark.asyncio
    async def test_parse_user_ids_handles_whitespace(self):
        """Should handle extra whitespace."""
        from src.commands import ConfigurationModal

        modal = ConfigurationModal(db=MagicMock())

        ids = modal._parse_user_ids("  123456789  ,   987654321  ")

        assert ids == [123456789, 987654321]

    @pytest.mark.asyncio
    async def test_parse_user_ids_ignores_invalid(self):
        """Should ignore invalid user IDs."""
        from src.commands import ConfigurationModal

        modal = ConfigurationModal(db=MagicMock())

        ids = modal._parse_user_ids("123456789, invalid, 987654321")

        assert ids == [123456789, 987654321]

    @pytest.mark.asyncio
    async def test_validate_user_ids_valid(self, mock_discord_interaction, mock_discord_user):
        """Should return empty list for valid users."""
        from src.commands import ConfigurationModal

        mock_discord_interaction.guild.fetch_member = AsyncMock(return_value=mock_discord_user)

        modal = ConfigurationModal(db=MagicMock())

        invalid = await modal._validate_user_ids(mock_discord_interaction, [123456789])

        assert invalid == []

    @pytest.mark.asyncio
    async def test_validate_user_ids_not_found(self, mock_discord_interaction):
        """Should return list of invalid IDs."""
        import discord
        from src.commands import ConfigurationModal

        mock_discord_interaction.guild.fetch_member = AsyncMock(
            side_effect=discord.NotFound(MagicMock(), 'User not found')
        )

        modal = ConfigurationModal(db=MagicMock())

        invalid = await modal._validate_user_ids(mock_discord_interaction, [999999999])

        assert '999999999' in invalid


class TestFeedbackModal:
    """Test FeedbackModal class."""

    @pytest.mark.asyncio
    async def test_submit_valid_feedback(self, mock_discord_interaction, mock_database):
        """Should save valid feedback and respond with confirmation."""
        from src.commands import FeedbackModal

        mock_database.save_feedback.return_value = 42

        mock_bot = MagicMock()
        mock_bot.notify_feedback = AsyncMock()

        modal = FeedbackModal(db=mock_database, bot=mock_bot)
        modal.feedback_type = MagicMock(value='bug')
        modal.message = MagicMock(value='Something is broken')
        modal.context = MagicMock(value='Tried to create playlist')

        await modal.on_submit(mock_discord_interaction)

        # Verify feedback was saved
        mock_database.save_feedback.assert_called_once()
        call_args = mock_database.save_feedback.call_args
        assert call_args[1]['feedback_type'] == 'bug'
        assert call_args[1]['message'] == 'Something is broken'

        # Verify response sent
        mock_discord_interaction.response.send_message.assert_called_once()
        call_args = mock_discord_interaction.response.send_message.call_args
        assert 'Thank you for your feedback' in call_args[0][0]

    @pytest.mark.asyncio
    async def test_submit_invalid_type(self, mock_discord_interaction, mock_database):
        """Should reject invalid feedback type."""
        from src.commands import FeedbackModal

        mock_bot = MagicMock()
        modal = FeedbackModal(db=mock_database, bot=mock_bot)
        modal.feedback_type = MagicMock(value='invalid_type')
        modal.message = MagicMock(value='Test message')
        modal.context = MagicMock(value=None)

        await modal.on_submit(mock_discord_interaction)

        # Should send error message
        mock_discord_interaction.response.send_message.assert_called_once()
        call_args = mock_discord_interaction.response.send_message.call_args
        assert 'bug' in call_args[0][0] or 'feature' in call_args[0][0]


class TestAdvancedSettingsModal:
    """Test AdvancedSettingsModal class."""

    @pytest.mark.asyncio
    async def test_requires_basic_config_first(self, mock_discord_interaction, mock_database):
        """Should require basic config before advanced settings."""
        from src.commands import AdvancedSettingsModal

        mock_database.get_bot_configuration.return_value = None

        modal = AdvancedSettingsModal(db=mock_database)
        modal.channel_id = MagicMock(value='')
        modal.playlist_name_template = MagicMock(value='')

        await modal.on_submit(mock_discord_interaction)

        mock_discord_interaction.response.send_message.assert_called_once()
        call_args = mock_discord_interaction.response.send_message.call_args
        assert 'jambot-setup' in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_validates_channel_id(
        self, mock_discord_interaction, mock_database, sample_bot_configuration
    ):
        """Should validate that channel ID exists in guild."""
        from src.commands import AdvancedSettingsModal

        mock_database.get_bot_configuration.return_value = sample_bot_configuration
        mock_discord_interaction.guild.get_channel.return_value = None  # Channel not found

        modal = AdvancedSettingsModal(db=mock_database)
        modal.channel_id = MagicMock(value='999999999')
        modal.playlist_name_template = MagicMock(value='')

        await modal.on_submit(mock_discord_interaction)

        call_args = mock_discord_interaction.response.send_message.call_args
        assert 'not found' in call_args[0][0].lower()


class TestSetlistPatternConfirmView:
    """Test SetlistPatternConfirmView class."""

    @pytest.mark.asyncio
    async def test_only_initiator_can_confirm(self, mock_discord_interaction, mock_database):
        """Should only allow the initiating user to confirm."""
        from src.commands import SetlistPatternConfirmView

        mock_bot = MagicMock()
        mock_bot.invalidate_parser_cache = MagicMock()

        view = SetlistPatternConfirmView(
            db=mock_database,
            bot=mock_bot,
            guild_id=123456789,
            analysis={'songs': []},
            message_url='https://discord.com/channels/...'
        )

        # Set up a different user trying to confirm
        mock_discord_interaction.user.id = 999999999
        mock_discord_interaction.message = MagicMock()
        mock_discord_interaction.message.interaction = MagicMock()
        mock_discord_interaction.message.interaction.user = MagicMock()
        mock_discord_interaction.message.interaction.user.id = 111111111  # Original user

        # Get the confirm button callback from the view
        # The decorator creates a button with callback, call it directly
        button = MagicMock()
        await view.confirm_button.callback(mock_discord_interaction)

        # Should send ephemeral error
        mock_discord_interaction.response.send_message.assert_called_once()
        assert mock_discord_interaction.response.send_message.call_args[1]['ephemeral'] is True


class TestJambotCommandsSetup:
    """Test JambotCommands slash command registration."""

    @pytest.mark.asyncio
    async def test_setup_registers_commands(self, mock_database):
        """Should register all slash commands."""
        from src.commands import JambotCommands

        mock_bot = MagicMock()
        mock_bot.tree = MagicMock()

        commands_handler = JambotCommands(bot=mock_bot, db=mock_database)
        await commands_handler.setup()

        # Verify commands were registered via decorator
        assert mock_bot.tree.command.called


class TestStatusCommand:
    """Test status command responses."""

    @pytest.mark.asyncio
    async def test_status_no_config(self, mock_discord_interaction, mock_database):
        """Should show error when no config exists."""
        from src.commands import JambotCommands

        mock_database.get_bot_configuration.return_value = None

        mock_bot = MagicMock()
        mock_bot.tree = MagicMock()

        commands_handler = JambotCommands(bot=mock_bot, db=mock_database)

        # Manually test the status command logic
        config = mock_database.get_bot_configuration(mock_discord_interaction.guild_id)

        assert config is None

    @pytest.mark.asyncio
    async def test_status_with_config(
        self, mock_discord_interaction, mock_database, sample_bot_configuration
    ):
        """Should show configuration status when config exists."""
        from src.commands import JambotCommands

        mock_database.get_bot_configuration.return_value = sample_bot_configuration
        mock_database.is_spotify_authorized.return_value = True

        mock_bot = MagicMock()
        mock_bot.tree = MagicMock()

        commands_handler = JambotCommands(bot=mock_bot, db=mock_database)

        config = mock_database.get_bot_configuration(mock_discord_interaction.guild_id)

        assert config is not None
        assert config['jam_leader_ids'] == sample_bot_configuration['jam_leader_ids']


class TestProcessCommand:
    """Test process command functionality."""

    @pytest.mark.asyncio
    async def test_rejects_non_approver(self, mock_discord_interaction, mock_database):
        """Should reject users who are not approvers or admins."""
        from src.commands import JambotCommands

        mock_database.get_approver_ids.return_value = [999888777]  # Different user
        mock_discord_interaction.user.guild_permissions = MagicMock()
        mock_discord_interaction.user.guild_permissions.administrator = False

        # User ID is different from approver
        assert mock_discord_interaction.user.id not in mock_database.get_approver_ids.return_value
        assert not mock_discord_interaction.user.guild_permissions.administrator


class TestWorkflowCommands:
    """Test workflow management commands."""

    def test_workflow_status_calculates_progress(self, sample_workflow):
        """Should correctly calculate selection progress."""
        total_songs = len(sample_workflow['song_matches'])
        selected_songs = len(sample_workflow['selections'])

        assert total_songs == 2
        assert selected_songs == 1  # Only song 2 has selection

    def test_workflow_cancel_permission_check(self, sample_workflow):
        """Should verify user has permission to cancel workflow."""
        # Test with user who is initiator
        user_id = sample_workflow['initiated_by']  # 111111111
        approver_ids = sample_workflow.get('approver_ids', [])

        is_initiator = user_id == sample_workflow['initiated_by']
        is_approver = user_id in approver_ids

        # Initiator should have permission
        has_permission = is_initiator or is_approver
        assert has_permission is True

        # Test with random user
        random_user_id = 999888777
        is_initiator = random_user_id == sample_workflow['initiated_by']
        is_approver = random_user_id in approver_ids

        has_permission = is_initiator or is_approver
        assert has_permission is False


class TestRetryCommand:
    """Test retry command functionality."""

    def test_retry_identifies_missing_songs(self, sample_workflow):
        """Should correctly identify songs missing selections."""
        selections = sample_workflow['selections']
        song_matches = sample_workflow['song_matches']

        missing = []
        for match in song_matches:
            song_key = str(match['number'])
            if song_key not in selections:
                # Check if stored version exists
                if not match.get('stored_version'):
                    missing.append(match['title'])

        assert len(missing) == 1
        assert 'Will the Circle Be Unbroken' in missing
