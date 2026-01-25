# Task ID: 18

**Title:** Design and Implement Premium API Database Schema

**Status:** pending

**Dependencies:** 17

**Priority:** high

**Description:** Create PostgreSQL tables for tenants, credits, credit_transactions, generation_history, products using Alembic migrations with indexes and connection pooling.

**Details:**

Use SQLAlchemy with asyncpg for pooling. Implement exact schema: tenants (UUID PK, discord_guild_id unique, api_token_hash bcrypt, api_token_prefix), credits (balance default 5), credit_transactions, generation_history (UUID PK), products. Add indexes on tenant_id, api_token_prefix, created_at. Generate Alembic migration: `alembic revision --autogenerate -m 'initial_schema'`, `alembic upgrade head`.

**Test Strategy:**

Run migrations, verify table schemas with `psql \d`, test insert/select on each table, confirm indexes exist, validate foreign keys and defaults.
