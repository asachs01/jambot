# Task ID: 28

**Title:** Implement Premium Setup Modal and Command

**Status:** pending

**Dependencies:** 27

**Priority:** medium

**Description:** Add /jambot-premium-setup slash command (admin only) with modal for token input, validation, and config storage.

**Details:**

Use discord.py app_commands, @app_commands.checks.has_permissions(administrator=True). Modal with TextInput(style=password). On submit: client.validate_token(token), hash=bcrypt.hashpw(token), save_premium_config(guild_id, hash, interaction.user.id), set premium_enabled=True. Ephemeral response with credits.

**Test Strategy:**

Test command hidden for non-admins, modal validation succeeds/fails, config saved with hash, enabled flag set.
