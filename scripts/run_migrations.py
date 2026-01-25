#!/usr/bin/env python3
"""Run Alembic database migrations."""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import Config
from alembic.config import Config as AlembicConfig
from alembic import command


def main():
    """Execute database migrations."""
    # Validate DATABASE_URL is configured
    if not Config.DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable is not set", file=sys.stderr)
        print("Please configure DATABASE_URL to run migrations", file=sys.stderr)
        sys.exit(1)

    print(f"Running migrations against database: {Config.DATABASE_URL.split('@')[1] if '@' in Config.DATABASE_URL else 'configured database'}")

    # Configure Alembic
    alembic_cfg = AlembicConfig(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))

    try:
        # Run migrations
        print("Upgrading database to head...")
        command.upgrade(alembic_cfg, "head")
        print("✓ Migrations completed successfully")

        # Verify tables exist
        print("\nVerifying tables...")
        import psycopg2
        conn = psycopg2.connect(Config.DATABASE_URL)
        cursor = conn.cursor()

        # Check for chord_charts table
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'chord_charts'
        """)
        if cursor.fetchone():
            print("✓ chord_charts table exists")
        else:
            print("✗ chord_charts table not found", file=sys.stderr)
            sys.exit(1)

        # Check for generation_history table
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'generation_history'
        """)
        if cursor.fetchone():
            print("✓ generation_history table exists")
        else:
            print("✗ generation_history table not found", file=sys.stderr)
            sys.exit(1)

        # Check for pg_trgm extension
        cursor.execute("""
            SELECT extname FROM pg_extension WHERE extname = 'pg_trgm'
        """)
        if cursor.fetchone():
            print("✓ pg_trgm extension enabled")
        else:
            print("⚠ pg_trgm extension not found (may require superuser to install)", file=sys.stderr)

        cursor.close()
        conn.close()

        print("\n✓ All migrations applied successfully!")
        return 0

    except Exception as e:
        print(f"\n✗ Migration failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
