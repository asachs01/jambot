# Database Migrations

This project uses [Alembic](https://alembic.sqlalchemy.org/) for managing PostgreSQL database schema migrations.

## Prerequisites

- PostgreSQL 16+ (required for latest JSONB features)
- Python 3.8+
- `alembic==1.13.1` installed (included in `requirements.txt`)
- PostgreSQL extensions:
  - `pg_trgm` - Required for fuzzy text matching (may need superuser to install)

## Configuration

Database connection is configured via the `DATABASE_URL` environment variable:

```bash
export DATABASE_URL="postgresql://user:password@host:port/database?sslmode=require"
```

Alternatively, use individual PostgreSQL environment variables:
```bash
export PGUSER=username
export PGPASS=password
export PGHOST=hostname
export PGPORT=25060
export PGDATABASE=dbname
export PGSSLMODE=require
```

## Running Migrations Locally

### Initial Setup

1. Ensure your database credentials are configured (see Configuration above)
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Apply All Migrations

Run the migration script:
```bash
python scripts/run_migrations.py
```

Or use Alembic directly:
```bash
alembic upgrade head
```

### Check Current Migration Status

```bash
alembic current
```

### View Migration History

```bash
alembic history --verbose
```

## Creating New Migrations

### Manual Migration Creation

1. Create a new migration file:
   ```bash
   alembic revision -m "description of changes"
   ```

2. Edit the generated file in `alembic/versions/` to add your schema changes
3. Implement both `upgrade()` and `downgrade()` functions

### Example Migration Structure

```python
def upgrade() -> None:
    # Add new column
    op.add_column('chord_charts', sa.Column('new_field', sa.String(100)))

    # Create index
    op.create_index('idx_new_field', 'chord_charts', ['new_field'])

def downgrade() -> None:
    # Remove index
    op.drop_index('idx_new_field', table_name='chord_charts')

    # Remove column
    op.drop_column('chord_charts', 'new_field')
```

## Migration Rollback

### Rollback to Previous Version

```bash
alembic downgrade -1
```

### Rollback to Specific Revision

```bash
alembic downgrade <revision_id>
```

### Rollback All Migrations

```bash
alembic downgrade base
```

**⚠️ Warning:** Rolling back migrations in production can result in data loss. Always backup your database before performing rollbacks.

## Testing Migrations

Run the migration test suite:

```bash
pytest tests/test_migrations.py -v
```

The test suite verifies:
- Tables are created with correct schema
- Indexes are properly configured
- Foreign key constraints work correctly
- JSONB operations function as expected
- Array columns work properly
- pg_trgm extension is enabled
- Migration upgrade/downgrade cycles work cleanly

## PostgreSQL Extension Installation

The `pg_trgm` extension is used for fuzzy text matching and similarity searches.

### Automatic Installation

The migration script attempts to install `pg_trgm` automatically:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Manual Installation (if automatic fails)

If you don't have superuser privileges, contact your database administrator to run:

```sql
-- Connect as superuser
psql -U postgres -d your_database

-- Enable extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Verifying Extension

```sql
SELECT extname FROM pg_extension WHERE extname = 'pg_trgm';
```

## Migration Files

### Current Migrations

- `001_create_chord_chart_tables.py` - Initial chord charts and generation history tables

### Migration File Structure

```
alembic/
├── versions/
│   └── 001_create_chord_chart_tables.py  # Migration scripts
├── env.py                                 # Alembic environment config
└── script.py.mako                         # Migration template

alembic.ini                                # Alembic configuration
scripts/
└── run_migrations.py                      # Migration execution script
```

## Schema Overview

### chord_charts Table

Stores chord chart data for songs:

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| title | VARCHAR(255) | Song title (required) |
| artist | VARCHAR(255) | Artist name |
| alternate_titles | TEXT[] | Alternative song titles |
| keys | VARCHAR(10)[] | Musical keys |
| lyrics | JSONB | Song lyrics data |
| chord_progression | JSONB | Chord progression data |
| source | VARCHAR(50) | Source of chart |
| status | VARCHAR(20) | Approval status |
| requested_by | BIGINT | Discord user ID who requested |
| approved_by | BIGINT | Discord user ID who approved |
| guild_id | BIGINT | Discord server ID (required) |
| created_at | TIMESTAMP | Creation timestamp |
| approved_at | TIMESTAMP | Approval timestamp |

**Constraints:**
- `UNIQUE(title, guild_id)` - One chart per title per server

**Indexes:**
- `idx_chord_charts_title_guild` - Unique index on title + guild_id
- `idx_chord_charts_status` - B-tree index on status
- `idx_chord_charts_guild_id` - B-tree index on guild_id
- `idx_chord_charts_lyrics_gin` - GIN index on lyrics JSONB
- `idx_chord_charts_chord_progression_gin` - GIN index on chord_progression JSONB

### generation_history Table

Tracks AI generation metrics:

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| chart_id | INTEGER | Foreign key to chord_charts (CASCADE delete) |
| model_used | VARCHAR(100) | AI model name |
| prompt_tokens | INTEGER | Input tokens consumed |
| completion_tokens | INTEGER | Output tokens generated |
| latency_ms | INTEGER | Generation time in milliseconds |
| cost_usd | DECIMAL(10,6) | Generation cost in USD |
| created_at | TIMESTAMP | Record timestamp |

**Constraints:**
- `FOREIGN KEY (chart_id) REFERENCES chord_charts(id) ON DELETE CASCADE`

**Indexes:**
- `idx_generation_history_chart_id` - B-tree index on chart_id

## Troubleshooting

### "No module named alembic"

Install dependencies:
```bash
pip install -r requirements.txt
```

### "DATABASE_URL environment variable is required"

Set your database connection string:
```bash
export DATABASE_URL="postgresql://user:pass@host:port/db?sslmode=require"
```

### "permission denied to create extension"

The `pg_trgm` extension requires superuser privileges. Contact your database administrator or use a managed database service that pre-installs common extensions.

### Migration conflicts

If you have multiple developers creating migrations:

1. Pull latest changes
2. Check for new migrations:
   ```bash
   alembic history
   ```
3. If conflicts exist, resolve by creating a merge migration:
   ```bash
   alembic merge -m "merge migrations" <rev1> <rev2>
   ```

## Production Deployment

### Pre-Deployment Checklist

- [ ] Test migrations on staging environment
- [ ] Backup production database
- [ ] Review all new migration scripts
- [ ] Verify rollback procedures are documented
- [ ] Ensure downtime window is scheduled (if required)

### Deployment Steps

1. Backup database:
   ```bash
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. Run migrations:
   ```bash
   python scripts/run_migrations.py
   ```

3. Verify schema:
   ```bash
   psql $DATABASE_URL -c "\d chord_charts"
   psql $DATABASE_URL -c "\d generation_history"
   ```

4. Test application functionality

### Rollback Procedure

If issues occur after deployment:

1. Stop application
2. Rollback migration:
   ```bash
   alembic downgrade -1
   ```
3. Restore from backup if needed:
   ```bash
   psql $DATABASE_URL < backup_file.sql
   ```
4. Investigate and fix migration issues
5. Re-test before re-deploying

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [PostgreSQL Array Types](https://www.postgresql.org/docs/current/arrays.html)
- [pg_trgm Extension](https://www.postgresql.org/docs/current/pgtrgm.html)
