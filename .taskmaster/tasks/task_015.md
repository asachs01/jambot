# Task ID: 15

**Title:** Add pytest test suite for JamBot Discord bot

**Status:** done

**Dependencies:** 2, 4, 5 ⧖, 6, 8, 11 ⧖, 12 ✓, 13 ✓

**Priority:** high

**Description:** Create comprehensive pytest test suite with tests/ directory structure, pytest.ini configuration, and test files for database operations, Discord command handlers, and bot workflow logic with mocked Discord.py and Spotify API responses.

**Details:**

DIRECTORY STRUCTURE:
Create the following test directory structure:
```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures and pytest configuration
├── test_database.py     # Database CRUD and migration tests
├── test_commands.py     # Slash command handler tests
├── test_bot.py          # Workflow logic and reaction handler tests
└── fixtures/
    ├── __init__.py
    ├── discord_fixtures.py   # Mock Discord objects
    └── spotify_fixtures.py   # Mock Spotify API responses
```

PYTEST.INI CONFIGURATION:
Create pytest.ini in project root:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    database: Database tests
    discord: Discord bot tests
    spotify: Spotify API tests
addopts = 
    -v
    --strict-markers
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --asyncio-mode=auto
```

CONFTEST.PY - SHARED FIXTURES:
```python
import pytest
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands

@pytest.fixture
def test_db():
    """Create in-memory test database"""
    conn = sqlite3.connect(':memory:')
    # Run schema creation from database.py
    cursor = conn.cursor()
    # Execute schema SQL
    yield conn
    conn.close()

@pytest.fixture
def mock_bot():
    """Mock Discord bot instance"""
    bot = MagicMock(spec=commands.Bot)
    bot.user = MagicMock(id=123456789)
    return bot

@pytest.fixture
def mock_guild():
    """Mock Discord guild"""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 987654321
    guild.name = "Test Server"
    return guild

@pytest.fixture
def mock_channel():
    """Mock Discord text channel"""
    channel = AsyncMock(spec=discord.TextChannel)
    channel.id = 111222333
    channel.send = AsyncMock()
    return channel

@pytest.fixture
def mock_user():
    """Mock Discord user"""
    user = MagicMock(spec=discord.User)
    user.id = 444555666
    user.name = "TestUser"
    user.send = AsyncMock()
    return user

@pytest.fixture
def mock_interaction():
    """Mock Discord interaction for slash commands"""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.user = MagicMock(id=444555666)
    return interaction
```

TEST_DATABASE.PY - DATABASE TESTS:
```python
import pytest
from src.database import (
    initialize_database,
    add_or_update_song,
    get_song_by_title,
    create_setlist,
    add_song_to_setlist,
    get_setlist_songs,
    run_migrations
)

@pytest.mark.database
def test_initialize_database(test_db):
    """Test database schema creation"""
    initialize_database(test_db)
    cursor = test_db.cursor()
    
    # Verify tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert 'songs' in tables
    assert 'setlists' in tables
    assert 'setlist_songs' in tables
    assert 'active_workflows' in tables

@pytest.mark.database
def test_add_or_update_song(test_db):
    """Test adding and updating songs"""
    initialize_database(test_db)
    
    # Add new song
    song_id = add_or_update_song(
        test_db,
        title="Blue Moon of Kentucky",
        spotify_track_id="abc123",
        artist="Bill Monroe",
        album="Test Album",
        spotify_url="https://open.spotify.com/track/abc123"
    )
    assert song_id is not None
    
    # Verify song exists
    song = get_song_by_title(test_db, "Blue Moon of Kentucky")
    assert song is not None
    assert song['artist'] == "Bill Monroe"
    
    # Update existing song
    updated_id = add_or_update_song(
        test_db,
        title="Blue Moon of Kentucky",
        spotify_track_id="xyz789",
        artist="Bill Monroe & His Blue Grass Boys",
        album="Updated Album",
        spotify_url="https://open.spotify.com/track/xyz789"
    )
    assert updated_id == song_id
    
    # Verify update
    updated_song = get_song_by_title(test_db, "Blue Moon of Kentucky")
    assert updated_song['spotify_track_id'] == "xyz789"

@pytest.mark.database
def test_create_setlist_and_add_songs(test_db):
    """Test setlist creation and song associations"""
    initialize_database(test_db)
    
    # Create setlist
    setlist_id = create_setlist(
        test_db,
        date="2024-01-15",
        guild_id=987654321,
        channel_id=111222333,
        playlist_url="https://open.spotify.com/playlist/test123"
    )
    assert setlist_id is not None
    
    # Add songs to setlist
    song1_id = add_or_update_song(test_db, "Song 1", "track1", "Artist 1", "Album 1", "url1")
    song2_id = add_or_update_song(test_db, "Song 2", "track2", "Artist 2", "Album 2", "url2")
    
    add_song_to_setlist(test_db, setlist_id, song1_id, position=1)
    add_song_to_setlist(test_db, setlist_id, song2_id, position=2)
    
    # Verify setlist songs
    songs = get_setlist_songs(test_db, setlist_id)
    assert len(songs) == 2
    assert songs[0]['position'] == 1
    assert songs[1]['position'] == 2

@pytest.mark.database
def test_migrations(test_db):
    """Test database migration system"""
    # Test migration execution
    run_migrations(test_db)
    
    # Verify migration tracking table exists
    cursor = test_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
    assert cursor.fetchone() is not None
```

TEST_COMMANDS.PY - SLASH COMMAND TESTS:
```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.commands import setup_slash_commands

@pytest.mark.discord
@pytest.mark.asyncio
async def test_setup_command_admin_only(mock_bot, mock_interaction):
    """Test /jambot setup command requires admin permissions"""
    setup_slash_commands(mock_bot)
    
    # Mock non-admin user
    mock_interaction.user.guild_permissions.administrator = False
    
    # Find setup command
    setup_command = next(cmd for cmd in mock_bot.tree.add_command.call_args_list 
                        if 'setup' in str(cmd))
    
    # Invoke command
    with pytest.raises(discord.errors.Forbidden):
        await setup_command(mock_interaction)

@pytest.mark.discord
@pytest.mark.asyncio
async def test_setup_command_modal_display(mock_bot, mock_interaction):
    """Test /jambot setup displays configuration modal"""
    setup_slash_commands(mock_bot)
    
    # Mock admin user
    mock_interaction.user.guild_permissions.administrator = True
    
    # Invoke setup command
    # Verify modal is sent
    mock_interaction.response.send_modal.assert_called_once()
    
    # Verify modal has correct fields
    modal = mock_interaction.response.send_modal.call_args[0][0]
    assert 'jam_leaders' in str(modal)
    assert 'approvers' in str(modal)
```

TEST_BOT.PY - WORKFLOW AND REACTION HANDLER TESTS:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.bot import JamBot

@pytest.fixture
def jam_bot(test_db, mock_bot):
    """Create JamBot instance with test database"""
    with patch('src.bot.discord.Client.__init__', return_value=None):
        bot = JamBot(database_conn=test_db)
        bot.user = mock_bot.user
        return bot

@pytest.mark.discord
@pytest.mark.asyncio
async def test_setlist_detection(jam_bot, mock_channel, mock_user):
    """Test setlist message detection and parsing"""
    # Mock jam leader message
    message = MagicMock()
    message.author = mock_user
    message.channel = mock_channel
    message.content = """
    Tonight's setlist:
    1. Blue Moon of Kentucky
    2. Foggy Mountain Breakdown
    3. Man of Constant Sorrow
    """
    
    with patch.object(jam_bot, 'is_jam_leader', return_value=True):
        await jam_bot.on_message(message)
    
    # Verify workflow created
    assert len(jam_bot.active_workflows) > 0

@pytest.mark.discord
@pytest.mark.asyncio
async def test_approval_reaction_handler(jam_bot, mock_user):
    """Test emoji reaction approval workflow"""
    # Create mock workflow
    workflow_id = 123456
    jam_bot.active_workflows[workflow_id] = {
        'guild_id': 987654321,
        'songs': ['Song 1', 'Song 2'],
        'selections': {0: {'spotify_track_id': 'track1'}, 1: {'spotify_track_id': 'track2'}},
        'approver_id': mock_user.id
    }
    
    # Mock reaction payload
    payload = MagicMock()
    payload.message_id = workflow_id
    payload.user_id = mock_user.id
    payload.emoji = MagicMock(name='✅')
    
    with patch.object(jam_bot, 'create_playlist_from_workflow', new_callable=AsyncMock) as mock_create:
        await jam_bot.on_raw_reaction_add(payload)
        mock_create.assert_called_once()

@pytest.mark.discord
@pytest.mark.asyncio
async def test_missing_songs_validation(jam_bot, mock_user):
    """Test workflow validation prevents playlist creation with missing songs"""
    # Create workflow with missing song
    workflow_id = 789012
    jam_bot.active_workflows[workflow_id] = {
        'guild_id': 987654321,
        'songs': ['Song 1', 'Song 2', 'Song 3'],
        'selections': {0: {'spotify_track_id': 'track1'}, 1: None, 2: {'spotify_track_id': 'track3'}},
        'approver_id': mock_user.id
    }
    
    payload = MagicMock()
    payload.message_id = workflow_id
    payload.user_id = mock_user.id
    payload.emoji = MagicMock(name='✅')
    
    with patch.object(jam_bot, 'create_playlist_from_workflow', new_callable=AsyncMock) as mock_create:
        await jam_bot.on_raw_reaction_add(payload)
        
        # Verify workflow not cleaned up (bug fix from Task 12)
        assert workflow_id in jam_bot.active_workflows

@pytest.mark.discord
@pytest.mark.asyncio
async def test_manual_dm_song_submission(jam_bot, mock_user, test_db):
    """Test manual song submission via DM persists to database immediately"""
    # Create workflow
    workflow_id = 345678
    jam_bot.active_workflows[workflow_id] = {
        'guild_id': 987654321,
        'songs': ['Unknown Song'],
        'selections': {0: None},
        'approver_id': mock_user.id
    }
    
    # Mock DM message with Spotify URL
    message = MagicMock()
    message.author = mock_user
    message.content = "https://open.spotify.com/track/manual123"
    message.channel = MagicMock(type=discord.ChannelType.private)
    
    with patch('src.bot.extract_spotify_track_id', return_value='manual123'):
        with patch('src.bot.get_track_details', return_value={
            'name': 'Manual Song',
            'artists': [{'name': 'Manual Artist'}],
            'album': {'name': 'Manual Album'},
            'external_urls': {'spotify': 'https://open.spotify.com/track/manual123'}
        }):
            await jam_bot.handle_dm_message(message)
    
    # Verify song persisted to database immediately (bug fix from Task 13)
    cursor = test_db.cursor()
    cursor.execute("SELECT * FROM songs WHERE spotify_track_id = ?", ('manual123',))
    song = cursor.fetchone()
    assert song is not None

@pytest.mark.spotify
@pytest.mark.asyncio
async def test_spotify_playlist_creation(jam_bot):
    """Test Spotify playlist creation with mocked API"""
    workflow = {
        'guild_id': 987654321,
        'channel_id': 111222333,
        'songs': ['Song 1', 'Song 2'],
        'selections': {
            0: {'spotify_track_id': 'track1', 'name': 'Song 1'},
            1: {'spotify_track_id': 'track2', 'name': 'Song 2'}
        }
    }
    
    with patch('src.bot.spotipy.Spotify') as mock_spotify:
        mock_spotify.return_value.user_playlists_create.return_value = {
            'id': 'playlist123',
            'external_urls': {'spotify': 'https://open.spotify.com/playlist/playlist123'}
        }
        
        playlist_url = await jam_bot.create_spotify_playlist(workflow)
        
        assert playlist_url == 'https://open.spotify.com/playlist/playlist123'
        mock_spotify.return_value.playlist_add_items.assert_called_once()
```

FIXTURES/SPOTIFY_FIXTURES.PY:
```python
import pytest

@pytest.fixture
def mock_spotify_search_response():
    """Mock Spotify search API response"""
    return {
        'tracks': {
            'items': [
                {
                    'id': 'track123',
                    'name': 'Blue Moon of Kentucky',
                    'artists': [{'name': 'Bill Monroe'}],
                    'album': {'name': 'The Essential Bill Monroe'},
                    'external_urls': {'spotify': 'https://open.spotify.com/track/track123'}
                }
            ]
        }
    }

@pytest.fixture
def mock_spotify_track_details():
    """Mock Spotify track details response"""
    return {
        'id': 'track456',
        'name': 'Foggy Mountain Breakdown',
        'artists': [{'name': 'Flatt & Scruggs'}],
        'album': {'name': 'Foggy Mountain Jamboree'},
        'external_urls': {'spotify': 'https://open.spotify.com/track/track456'}
    }
```

DEPENDENCIES:
Install required testing packages:
```
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

Add to requirements-dev.txt:
```
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
```

**Test Strategy:**

1. **Test Suite Execution:**
   - Run `pytest` from project root and verify all tests are discovered
   - Confirm pytest.ini configuration is loaded correctly
   - Verify asyncio_mode=auto enables async test execution
   - Check that coverage report is generated in htmlcov/ directory

2. **Database Tests Validation:**
   - Run `pytest tests/test_database.py -v` and verify all CRUD tests pass
   - Confirm in-memory database fixture creates clean state for each test
   - Test schema creation, song insertion, updates, and setlist operations
   - Verify migration tests execute without errors
   - Check that database constraints (unique, foreign keys) are enforced

3. **Command Handler Tests:**
   - Run `pytest tests/test_commands.py -v -m discord`
   - Verify slash command registration mocks work correctly
   - Test admin permission checks prevent unauthorized access
   - Confirm modal display and submission handling
   - Validate interaction response mocking

4. **Bot Workflow Tests:**
   - Run `pytest tests/test_bot.py -v -m discord`
   - Test setlist detection and parsing from messages
   - Verify reaction handler creates playlists on ✅ approval
   - Confirm missing song validation prevents premature playlist creation
   - Test manual DM song submission persists to database immediately (Task 13 fix)
   - Verify workflow cleanup preserves active workflows when songs missing (Task 12 fix)

5. **Spotify API Mocking:**
   - Run `pytest -v -m spotify`
   - Verify mock Spotify search returns expected track data
   - Test playlist creation with mocked spotipy client
   - Confirm track addition to playlist works with fixtures
   - Validate error handling for API failures

6. **Coverage Analysis:**
   - Run `pytest --cov=src --cov-report=term-missing`
   - Verify coverage is at least 80% for database.py, commands.py, bot.py
   - Review coverage report to identify untested code paths
   - Add additional tests for any critical uncovered lines

7. **Integration Testing:**
   - Run `pytest -v -m integration` for end-to-end workflow tests
   - Test complete flow: setlist detection → song matching → approval → playlist creation
   - Verify database persistence across workflow stages
   - Confirm Discord and Spotify mocks integrate correctly

8. **Continuous Integration:**
   - Add pytest to CI/CD pipeline
   - Verify tests run automatically on pull requests
   - Confirm test failures block merges
   - Check coverage reports are published
