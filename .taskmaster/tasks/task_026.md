# Task ID: 26

**Title:** Add Premium Configuration to Bot Database

**Status:** pending

**Dependencies:** None

**Priority:** medium

**Description:** Extend JamBot bot_configuration table with premium_api_token_hash, premium_enabled, premium_setup_by, premium_setup_at.

**Details:**

Run ALTER TABLE bot_configuration ADD COLUMN premium_api_token_hash VARCHAR(72), ADD premium_enabled BOOLEAN DEFAULT FALSE, ADD premium_setup_by BIGINT, ADD premium_setup_at TIMESTAMP. Implement asyncpg functions save_premium_config(guild_id, token_hash, setup_by), get_premium_config(guild_id), is_premium_enabled(guild_id).

**Test Strategy:**

Apply schema changes, test insert/retrieve config, hash verification with bcrypt.checkpw, enabled flag updates correctly.
