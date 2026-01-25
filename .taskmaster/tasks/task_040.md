# Task ID: 40

**Title:** Extend Bot Database for Premium Configuration

**Status:** cancelled

**Dependencies:** None

**Priority:** medium

**Description:** Add premium columns to bot_configuration table and create DB methods.

**Details:**

Run migration: ALTER TABLE bot_configuration ADD premium_api_token_hash VARCHAR(72), premium_enabled BOOLEAN DEFAULT FALSE, premium_setup_by BIGINT, premium_setup_at TIMESTAMP. Create async def save_premium_config(guild_id, token_hash, setup_by), get_premium_config(guild_id), is_premium_enabled(guild_id). Use bcrypt.hashpw(token, bcrypt.gensalt()).

**Test Strategy:**

Test migration doesn't break existing data, CRUD operations on new columns, token hashing/verification, premium_enabled toggle.
