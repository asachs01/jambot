"""Tests for Alembic database migrations."""
import pytest
import psycopg2
import psycopg2.extras
import os
import json
from decimal import Decimal
from alembic.config import Config as AlembicConfig
from alembic import command
from pathlib import Path


@pytest.fixture
def alembic_config(test_db_url):
    """Create Alembic configuration."""
    project_root = Path(__file__).parent.parent
    cfg = AlembicConfig(str(project_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(project_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", test_db_url)
    return cfg


@pytest.fixture
def test_db_url():
    """Get test database URL from environment."""
    url = os.environ.get('DATABASE_URL', 'postgresql://test:test@localhost:5432/test')
    return url


@pytest.fixture(scope="function")
def db_connection(test_db_url, alembic_config):
    """Create test database connection with migrations applied."""
    # Clean up any existing tables
    conn = psycopg2.connect(test_db_url)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS generation_history CASCADE")
    cursor.execute("DROP TABLE IF EXISTS chord_charts CASCADE")
    cursor.execute("DROP TABLE IF EXISTS alembic_version CASCADE")
    conn.commit()
    cursor.close()
    conn.close()

    # Run migrations
    command.upgrade(alembic_config, "head")

    # Create new connection
    conn = psycopg2.connect(test_db_url)
    yield conn

    # Cleanup
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS generation_history CASCADE")
    cursor.execute("DROP TABLE IF EXISTS chord_charts CASCADE")
    cursor.execute("DROP TABLE IF EXISTS alembic_version CASCADE")
    conn.commit()
    cursor.close()
    conn.close()


def test_migration_upgrade_creates_tables(db_connection):
    """Test that migration upgrade creates both tables."""
    # Migration already run by db_connection fixture
    cursor = db_connection.cursor()

    # Verify chord_charts table exists
    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'chord_charts'
    """)
    assert cursor.fetchone() is not None, "chord_charts table should exist"

    # Verify generation_history table exists
    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'generation_history'
    """)
    assert cursor.fetchone() is not None, "generation_history table should exist"

    cursor.close()


def test_chord_charts_schema(db_connection):
    """Verify chord_charts table has correct schema."""
    cursor = db_connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get column definitions
    cursor.execute("""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'chord_charts'
        ORDER BY ordinal_position
    """)
    columns = {row['column_name']: row for row in cursor.fetchall()}

    # Verify required columns exist
    required_columns = [
        'id', 'title', 'artist', 'alternate_titles', 'keys',
        'lyrics', 'chord_progression', 'source', 'status',
        'requested_by', 'approved_by', 'guild_id',
        'created_at', 'approved_at'
    ]
    for col in required_columns:
        assert col in columns, f"Column {col} should exist"

    # Verify specific column properties
    assert columns['title']['character_maximum_length'] == 255
    assert columns['artist']['character_maximum_length'] == 255
    assert columns['title']['is_nullable'] == 'NO'
    assert columns['guild_id']['is_nullable'] == 'NO'

    cursor.close()


def test_generation_history_schema(db_connection):
    """Verify generation_history table has correct schema."""
    cursor = db_connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'generation_history'
        ORDER BY ordinal_position
    """)
    columns = {row['column_name']: row for row in cursor.fetchall()}

    # Verify required columns
    required_columns = [
        'id', 'chart_id', 'model_used', 'prompt_tokens',
        'completion_tokens', 'latency_ms', 'cost_usd', 'created_at'
    ]
    for col in required_columns:
        assert col in columns, f"Column {col} should exist"

    # Verify NOT NULL constraints
    assert columns['chart_id']['is_nullable'] == 'NO'
    assert columns['model_used']['is_nullable'] == 'NO'
    assert columns['prompt_tokens']['is_nullable'] == 'NO'

    cursor.close()


def test_indexes_created(db_connection):
    """Verify all required indexes are created."""
    cursor = db_connection.cursor()

    # Get all indexes
    cursor.execute("""
        SELECT indexname FROM pg_indexes
        WHERE tablename IN ('chord_charts', 'generation_history')
    """)
    indexes = {row[0] for row in cursor.fetchall()}

    # Verify required indexes exist
    required_indexes = [
        'idx_chord_charts_title_guild',
        'idx_chord_charts_status',
        'idx_chord_charts_guild_id',
        'idx_chord_charts_lyrics_gin',
        'idx_chord_charts_chord_progression_gin',
        'idx_generation_history_chart_id'
    ]

    for idx in required_indexes:
        assert idx in indexes, f"Index {idx} should exist"

    cursor.close()


def test_foreign_key_constraint(db_connection):
    """Test that foreign key constraint exists and works."""
    cursor = db_connection.cursor()

    # Insert test chord chart
    cursor.execute("""
        INSERT INTO chord_charts (title, guild_id, keys)
        VALUES ('Test Song', 123, ARRAY['G', 'C'])
        RETURNING id
    """)
    chart_id = cursor.fetchone()[0]

    # Insert generation history record
    cursor.execute("""
        INSERT INTO generation_history
        (chart_id, model_used, prompt_tokens, completion_tokens, latency_ms, cost_usd)
        VALUES (%s, 'test-model', 100, 200, 1500, 0.001)
        RETURNING id
    """, (chart_id,))
    history_id = cursor.fetchone()[0]
    db_connection.commit()

    # Verify record was inserted
    cursor.execute("SELECT id FROM generation_history WHERE id = %s", (history_id,))
    assert cursor.fetchone() is not None

    # Delete chord chart - should cascade delete generation_history
    cursor.execute("DELETE FROM chord_charts WHERE id = %s", (chart_id,))
    db_connection.commit()

    # Verify generation_history record was deleted
    cursor.execute("SELECT id FROM generation_history WHERE id = %s", (history_id,))
    assert cursor.fetchone() is None, "Foreign key cascade delete should remove generation_history record"

    cursor.close()


def test_unique_constraint(db_connection):
    """Test unique constraint on title and guild_id."""
    cursor = db_connection.cursor()

    # Insert first record
    cursor.execute("""
        INSERT INTO chord_charts (title, guild_id, keys)
        VALUES ('Unique Song', 456, ARRAY['A'])
    """)
    db_connection.commit()

    # Try to insert duplicate - should fail
    with pytest.raises(psycopg2.IntegrityError):
        cursor.execute("""
            INSERT INTO chord_charts (title, guild_id, keys)
            VALUES ('Unique Song', 456, ARRAY['D'])
        """)
        db_connection.commit()

    db_connection.rollback()

    # Same title, different guild - should succeed
    cursor.execute("""
        INSERT INTO chord_charts (title, guild_id, keys)
        VALUES ('Unique Song', 789, ARRAY['D'])
    """)
    db_connection.commit()

    cursor.close()


def test_jsonb_operations(db_connection):
    """Test JSONB column operations."""
    cursor = db_connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Insert chart with JSONB data
    lyrics_data = {
        "verse1": "Amazing grace, how sweet the sound",
        "chorus": "Saved a wretch like me"
    }
    chord_progression_data = {
        "verse": ["G", "C", "G", "D"],
        "chorus": ["G", "Em", "C", "D"]
    }

    cursor.execute("""
        INSERT INTO chord_charts
        (title, guild_id, keys, lyrics, chord_progression)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, ('Amazing Grace', 999, ['G'], json.dumps(lyrics_data), json.dumps(chord_progression_data)))
    chart_id = cursor.fetchone()['id']
    db_connection.commit()

    # Query using JSONB operators
    cursor.execute("""
        SELECT id, lyrics->>'verse1' as verse1, chord_progression->'verse' as verse_chords
        FROM chord_charts
        WHERE id = %s
    """, (chart_id,))
    row = cursor.fetchone()

    assert row['verse1'] == "Amazing grace, how sweet the sound"
    assert row['verse_chords'] == ["G", "C", "G", "D"]

    cursor.close()


def test_array_columns(db_connection):
    """Test array column operations."""
    cursor = db_connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Insert with arrays
    cursor.execute("""
        INSERT INTO chord_charts
        (title, guild_id, keys, alternate_titles)
        VALUES (%s, %s, %s, %s)
        RETURNING id, keys, alternate_titles
    """, ('Test Arrays', 111, ['G', 'A', 'D'], ['Test', 'Arrays', 'Song']))
    row = cursor.fetchone()
    db_connection.commit()

    assert row['keys'] == ['G', 'A', 'D']
    assert row['alternate_titles'] == ['Test', 'Arrays', 'Song']

    cursor.close()


def test_pg_trgm_extension(db_connection):
    """Test that pg_trgm extension is enabled."""
    cursor = db_connection.cursor()

    cursor.execute("""
        SELECT extname FROM pg_extension WHERE extname = 'pg_trgm'
    """)
    assert cursor.fetchone() is not None, "pg_trgm extension should be enabled"

    cursor.close()


def test_gin_index_usage(db_connection):
    """Test that GIN indexes exist for JSONB queries."""
    cursor = db_connection.cursor()

    # Verify GIN index exists on lyrics column
    cursor.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'chord_charts'
        AND indexname = 'idx_chord_charts_lyrics_gin'
    """)
    lyrics_index = cursor.fetchone()
    assert lyrics_index is not None, "GIN index on lyrics should exist"
    assert 'gin' in lyrics_index[1].lower(), "Index should be GIN type"

    # Verify GIN index exists on chord_progression column
    cursor.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'chord_charts'
        AND indexname = 'idx_chord_charts_chord_progression_gin'
    """)
    chord_index = cursor.fetchone()
    assert chord_index is not None, "GIN index on chord_progression should exist"
    assert 'gin' in chord_index[1].lower(), "Index should be GIN type"

    cursor.close()


def test_migration_downgrade(alembic_config, db_connection):
    """Test that downgrade removes tables cleanly."""
    cursor = db_connection.cursor()

    # Already at head from db_connection fixture
    # Downgrade to base
    command.downgrade(alembic_config, "base")

    # Verify tables are removed
    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name IN ('chord_charts', 'generation_history')
    """)
    assert cursor.fetchone() is None, "Tables should be removed after downgrade"

    cursor.close()


def test_decimal_precision(db_connection):
    """Test DECIMAL precision for cost_usd column."""
    cursor = db_connection.cursor()

    # Insert chart
    cursor.execute("""
        INSERT INTO chord_charts (title, guild_id, keys)
        VALUES ('Cost Test', 333, ARRAY['E'])
        RETURNING id
    """)
    chart_id = cursor.fetchone()[0]

    # Insert with precise decimal
    test_cost = Decimal('0.123456')
    cursor.execute("""
        INSERT INTO generation_history
        (chart_id, model_used, prompt_tokens, completion_tokens, latency_ms, cost_usd)
        VALUES (%s, 'test', 50, 100, 500, %s)
    """, (chart_id, test_cost))
    db_connection.commit()

    # Retrieve and verify precision
    cursor.execute("""
        SELECT cost_usd FROM generation_history WHERE chart_id = %s
    """, (chart_id,))
    retrieved_cost = cursor.fetchone()[0]

    assert retrieved_cost == test_cost, "Decimal precision should be preserved"

    cursor.close()


def test_database_record_chart_generation(db_connection, test_db_url):
    """Test Database.record_chart_generation() method."""
    # Import Database class
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
    from database import Database

    # Create Database instance with test database URL
    db = Database(test_db_url)

    # Insert test chart directly via psycopg2
    cursor = db_connection.cursor()
    cursor.execute("""
        INSERT INTO chord_charts (title, guild_id, keys)
        VALUES ('Generation Test', 444, ARRAY['F'])
        RETURNING id
    """)
    chart_id = cursor.fetchone()[0]
    db_connection.commit()
    cursor.close()

    # Test record_chart_generation method
    history_id = db.record_chart_generation(
        chart_id=chart_id,
        model_used='test-model-v1',
        prompt_tokens=150,
        completion_tokens=300,
        latency_ms=2000,
        cost_usd=Decimal('0.005000')
    )

    # Verify record was inserted
    cursor = db_connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT * FROM generation_history WHERE id = %s
    """, (history_id,))
    record = cursor.fetchone()

    assert record is not None, "Generation history record should exist"
    assert record['chart_id'] == chart_id
    assert record['model_used'] == 'test-model-v1'
    assert record['prompt_tokens'] == 150
    assert record['completion_tokens'] == 300
    assert record['latency_ms'] == 2000
    assert record['cost_usd'] == Decimal('0.005000')

    cursor.close()


def test_database_get_chart_generation_history(db_connection, test_db_url):
    """Test Database.get_chart_generation_history() method."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
    from database import Database

    db = Database(test_db_url)

    # Create test chart
    cursor = db_connection.cursor()
    cursor.execute("""
        INSERT INTO chord_charts (title, guild_id, keys)
        VALUES ('History Test', 555, ARRAY['B'])
        RETURNING id
    """)
    chart_id = cursor.fetchone()[0]
    db_connection.commit()
    cursor.close()

    # Record multiple generation events
    db.record_chart_generation(chart_id, 'model-1', 100, 200, 1000, Decimal('0.001'))
    db.record_chart_generation(chart_id, 'model-2', 150, 250, 1500, Decimal('0.002'))
    db.record_chart_generation(chart_id, 'model-1', 120, 220, 1200, Decimal('0.0015'))

    # Retrieve history
    history = db.get_chart_generation_history(chart_id)

    assert len(history) == 3, "Should have 3 generation history records"

    # Verify ordering (newest first)
    assert history[0]['model_used'] == 'model-1', "Newest record should be first"
    assert history[0]['prompt_tokens'] == 120

    # Verify all fields present
    required_fields = ['id', 'chart_id', 'model_used', 'prompt_tokens',
                      'completion_tokens', 'latency_ms', 'cost_usd', 'created_at']
    for field in required_fields:
        assert field in history[0], f"Field {field} should be present"


def test_database_get_generation_stats(db_connection, test_db_url):
    """Test Database.get_generation_stats() method."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
    from database import Database

    db = Database(test_db_url)

    # Create test charts for two guilds
    cursor = db_connection.cursor()
    cursor.execute("""
        INSERT INTO chord_charts (title, guild_id, keys)
        VALUES ('Stats Test 1', 666, ARRAY['G'])
        RETURNING id
    """)
    chart_id_1 = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO chord_charts (title, guild_id, keys)
        VALUES ('Stats Test 2', 666, ARRAY['C'])
        RETURNING id
    """)
    chart_id_2 = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO chord_charts (title, guild_id, keys)
        VALUES ('Stats Test 3', 777, ARRAY['D'])
        RETURNING id
    """)
    chart_id_3 = cursor.fetchone()[0]
    db_connection.commit()
    cursor.close()

    # Record generations across different guilds and models
    db.record_chart_generation(chart_id_1, 'gpt-4', 100, 200, 1000, Decimal('0.010'))
    db.record_chart_generation(chart_id_1, 'gpt-4', 120, 220, 1100, Decimal('0.011'))
    db.record_chart_generation(chart_id_2, 'claude-3', 150, 250, 1200, Decimal('0.015'))
    db.record_chart_generation(chart_id_3, 'gpt-4', 130, 230, 1050, Decimal('0.012'))

    # Test stats for all guilds
    all_stats = db.get_generation_stats(days=30)
    assert all_stats['total_generations'] == 4
    assert all_stats['total_cost_usd'] == Decimal('0.048')
    assert all_stats['total_prompt_tokens'] == 500
    assert all_stats['total_completion_tokens'] == 900
    assert 'avg_latency_ms' in all_stats
    assert len(all_stats['by_model']) == 2  # gpt-4 and claude-3

    # Test stats filtered by guild_id
    guild_stats = db.get_generation_stats(guild_id=666, days=30)
    assert guild_stats['total_generations'] == 3
    assert guild_stats['total_cost_usd'] == Decimal('0.036')

    # Verify by_model breakdown
    model_names = {model['model_used'] for model in all_stats['by_model']}
    assert 'gpt-4' in model_names
    assert 'claude-3' in model_names
