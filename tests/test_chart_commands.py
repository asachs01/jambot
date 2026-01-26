"""Integration tests for chord chart commands with rate limiting."""
import pytest
import discord
from unittest.mock import AsyncMock, MagicMock, patch
from src.chart_commands import ChartCommands
from src.rate_limiter import RateLimiter


@pytest.fixture
def mock_bot():
    """Create a mock Discord bot."""
    bot = MagicMock()
    bot.tree = MagicMock()
    return bot


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = MagicMock()
    db.get_chord_chart = MagicMock(return_value=None)
    db.search_chord_charts = MagicMock(return_value=[])
    return db


@pytest.fixture
async def mock_rate_limiter():
    """Create a mock rate limiter."""
    limiter = MagicMock(spec=RateLimiter)
    limiter.check_rate_limit = AsyncMock(return_value=(True, 2))
    limiter.get_ttl = AsyncMock(return_value=600)
    return limiter


@pytest.fixture
def mock_interaction():
    """Create a mock Discord interaction."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.user = MagicMock()
    interaction.user.id = 123456
    interaction.guild_id = 789012
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction


@pytest.mark.asyncio
async def test_view_chord_chart_with_rate_limit_allowed(
    mock_bot, mock_db, mock_rate_limiter, mock_interaction
):
    """Test viewing chord chart when rate limit allows."""
    # Setup mock data
    mock_db.get_chord_chart.return_value = {
        'id': 1,
        'title': 'Mountain Dew',
        'chart_title': 'Mountain Dew',
        'keys': [{'key': 'G', 'sections': []}],
        'lyrics': None
    }

    chart_commands = ChartCommands(mock_bot, mock_db, rate_limiter=mock_rate_limiter)

    with patch('src.chart_commands.generate_chart_pdf') as mock_generate:
        mock_generate.return_value = MagicMock()

        await chart_commands._handle_view(mock_interaction, 'Mountain Dew', None)

        # Verify rate limit was checked
        mock_rate_limiter.check_rate_limit.assert_called_once_with('user:123456:chord')

        # Verify chart was generated
        mock_generate.assert_called_once()
        mock_interaction.followup.send.assert_called_once()


@pytest.mark.asyncio
async def test_view_chord_chart_rate_limit_exceeded(
    mock_bot, mock_db, mock_rate_limiter, mock_interaction
):
    """Test viewing chord chart when rate limit is exceeded."""
    # Rate limit returns False (exceeded)
    mock_rate_limiter.check_rate_limit = AsyncMock(return_value=(False, 0))
    mock_rate_limiter.get_ttl = AsyncMock(return_value=420)  # 7 minutes

    chart_commands = ChartCommands(mock_bot, mock_db, rate_limiter=mock_rate_limiter)

    await chart_commands._handle_view(mock_interaction, 'Mountain Dew', None)

    # Verify rate limit error was sent
    mock_interaction.response.send_message.assert_called_once()
    call_args = mock_interaction.response.send_message.call_args
    assert '⏱️' in call_args[0][0]
    assert 'Rate limit exceeded' in call_args[0][0]
    assert call_args[1]['ephemeral'] is True


@pytest.mark.asyncio
async def test_transpose_chord_chart_with_rate_limit(
    mock_bot, mock_db, mock_rate_limiter, mock_interaction
):
    """Test transposing chord chart with rate limiting."""
    mock_db.get_chord_chart.return_value = {
        'id': 1,
        'title': 'Mountain Dew',
        'chart_title': 'Mountain Dew',
        'keys': [{'key': 'G', 'sections': []}],
        'lyrics': None
    }

    chart_commands = ChartCommands(mock_bot, mock_db, rate_limiter=mock_rate_limiter)

    with patch('src.chart_commands.generate_chart_pdf') as mock_generate, \
         patch('src.chart_commands.transpose_key_entry') as mock_transpose:

        mock_generate.return_value = MagicMock()
        mock_transpose.return_value = {'key': 'A', 'sections': []}

        await chart_commands._handle_transpose(mock_interaction, 'Mountain Dew', 'A')

        # Verify rate limit was checked
        mock_rate_limiter.check_rate_limit.assert_called_once_with('user:123456:chord')

        # Verify transpose was called
        mock_transpose.assert_called_once()


@pytest.mark.asyncio
async def test_chart_commands_without_rate_limiter(
    mock_bot, mock_db, mock_interaction
):
    """Test chart commands work without rate limiter (graceful degradation)."""
    mock_db.get_chord_chart.return_value = {
        'id': 1,
        'title': 'Mountain Dew',
        'keys': [{'key': 'G', 'sections': []}],
    }

    # Create chart commands without rate limiter
    chart_commands = ChartCommands(mock_bot, mock_db, rate_limiter=None)

    with patch('src.chart_commands.generate_chart_pdf') as mock_generate:
        mock_generate.return_value = MagicMock()

        # Should work without rate limiting
        await chart_commands._handle_view(mock_interaction, 'Mountain Dew', None)

        mock_generate.assert_called_once()


@pytest.mark.asyncio
async def test_handle_mention_with_rate_limit(mock_bot, mock_db, mock_rate_limiter):
    """Test mention-based chart request with rate limiting."""
    mock_message = AsyncMock()
    mock_message.content = '@jambot chart for Mountain Dew'
    mock_message.author.id = 123456
    mock_message.guild.id = 789012
    mock_message.reply = AsyncMock()

    mock_db.get_chord_chart.return_value = {
        'id': 1,
        'title': 'Mountain Dew',
        'keys': [{'key': 'G', 'sections': []}],
    }

    chart_commands = ChartCommands(mock_bot, mock_db, rate_limiter=mock_rate_limiter)

    with patch('src.chart_commands.generate_chart_pdf') as mock_generate:
        mock_generate.return_value = MagicMock()

        await chart_commands.handle_mention(mock_message)

        # Verify rate limit was checked
        mock_rate_limiter.check_rate_limit.assert_called_once_with('user:123456:chord')


@pytest.mark.asyncio
async def test_handle_mention_rate_limit_exceeded(mock_bot, mock_db, mock_rate_limiter):
    """Test mention-based request when rate limited."""
    mock_message = AsyncMock()
    mock_message.content = '@jambot chart for Mountain Dew'
    mock_message.author.id = 123456
    mock_message.guild.id = 789012
    mock_message.reply = AsyncMock()

    # Rate limit exceeded
    mock_rate_limiter.check_rate_limit = AsyncMock(return_value=(False, 0))
    mock_rate_limiter.get_ttl = AsyncMock(return_value=540)  # 9 minutes

    chart_commands = ChartCommands(mock_bot, mock_db, rate_limiter=mock_rate_limiter)

    await chart_commands.handle_mention(mock_message)

    # Verify rate limit message was sent
    mock_message.reply.assert_called_once()
    call_args = mock_message.reply.call_args[0][0]
    assert 'Rate limit exceeded' in call_args


@pytest.mark.asyncio
async def test_rate_limit_remaining_count_message(
    mock_bot, mock_db, mock_rate_limiter, mock_interaction
):
    """Test that success messages include remaining request count."""
    mock_db.get_chord_chart.return_value = {
        'id': 1,
        'title': 'Mountain Dew',
        'keys': [{'key': 'G', 'sections': []}],
    }

    # First request - 2 remaining
    mock_rate_limiter.check_rate_limit = AsyncMock(return_value=(True, 2))

    chart_commands = ChartCommands(mock_bot, mock_db, rate_limiter=mock_rate_limiter)

    with patch('src.chart_commands.generate_chart_pdf') as mock_generate:
        mock_generate.return_value = MagicMock()

        await chart_commands._handle_view(mock_interaction, 'Mountain Dew', None)

        # Verify message includes remaining count
        call_args = mock_interaction.followup.send.call_args[0][0]
        assert '2 requests remaining' in call_args or 'remaining' in call_args.lower()


@pytest.mark.asyncio
async def test_create_request_not_rate_limited(mock_bot, mock_db, mock_rate_limiter):
    """Test that create requests via mention are NOT rate limited."""
    mock_message = AsyncMock()
    mock_message.content = '@jambot create a chord chart for New Song'
    mock_message.author.id = 123456
    mock_message.reply = AsyncMock()

    chart_commands = ChartCommands(mock_bot, mock_db, rate_limiter=mock_rate_limiter)

    with patch('src.chart_commands.CreateChartView'):
        await chart_commands.handle_mention(mock_message)

        # Create requests should NOT check rate limit
        mock_rate_limiter.check_rate_limit.assert_not_called()
