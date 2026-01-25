"""create chord chart tables

Revision ID: 001
Revises:
Create Date: 2026-01-25 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pg_trgm extension for fuzzy matching
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    # Create chord_charts table
    op.execute("""
        CREATE TABLE chord_charts (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            artist VARCHAR(255),
            alternate_titles TEXT[],
            keys VARCHAR(10)[],
            lyrics JSONB,
            chord_progression JSONB,
            source VARCHAR(50),
            status VARCHAR(20),
            requested_by BIGINT,
            approved_by BIGINT,
            guild_id BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            approved_at TIMESTAMP
        )
    """)

    # Create generation_history table
    op.execute("""
        CREATE TABLE generation_history (
            id SERIAL PRIMARY KEY,
            chart_id INTEGER NOT NULL REFERENCES chord_charts(id) ON DELETE CASCADE,
            model_used VARCHAR(100) NOT NULL,
            prompt_tokens INTEGER NOT NULL,
            completion_tokens INTEGER NOT NULL,
            latency_ms INTEGER NOT NULL,
            cost_usd DECIMAL(10,6) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create indexes for chord_charts
    op.execute('CREATE UNIQUE INDEX idx_chord_charts_title_guild ON chord_charts(title, guild_id)')
    op.execute('CREATE INDEX idx_chord_charts_status ON chord_charts(status)')
    op.execute('CREATE INDEX idx_chord_charts_guild_id ON chord_charts(guild_id)')
    op.execute('CREATE INDEX idx_chord_charts_lyrics_gin ON chord_charts USING GIN(lyrics)')
    op.execute('CREATE INDEX idx_chord_charts_chord_progression_gin ON chord_charts USING GIN(chord_progression)')

    # Create index for generation_history
    op.execute('CREATE INDEX idx_generation_history_chart_id ON generation_history(chart_id)')


def downgrade() -> None:
    # Drop tables (cascade will handle generation_history automatically)
    op.execute('DROP TABLE IF EXISTS generation_history CASCADE')
    op.execute('DROP TABLE IF EXISTS chord_charts CASCADE')

    # Note: We don't drop pg_trgm extension in case other tables use it
