# Task ID: 32

**Title:** Implement Premium API Database Schema

**Status:** cancelled

**Dependencies:** 31 ✗

**Priority:** high

**Description:** Create PostgreSQL tables for tenants, credits, transactions, generation history, and products using Alembic migrations.

**Details:**

Use SQLAlchemy with asyncpg for connection pooling. Define models matching exact schema: tenants (UUID PK, discord_guild_id unique, api_token_hash bcrypt, api_token_prefix), credits (balance default 5, trial_used), credit_transactions, generation_history (UUID PK), products. Create Alembic env.py with async engine. Add indexes: tenants(discord_guild_id, api_token_prefix), credits(tenant_id), credit_transactions(tenant_id). Run `alembic init migrations`, `alembic revision --autogenerate`, `alembic upgrade head`.

**Test Strategy:**

Run migrations on test DB, verify table schemas with psql \d, test insert/select on each table, confirm indexes exist, validate foreign key constraints.
