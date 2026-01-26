# Task ID: 42

**Title:** Implement Premium Setup Command and Modal

**Status:** cancelled

**Dependencies:** 40 ✗, 41 ✗

**Priority:** medium

**Description:** Add /jambot-premium-setup slash command with token validation modal.

**Details:**

Create PremiumSetupModal with TextInput(label='API Token', style=password). In callback: client.validate_token(token), hash=bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode(), save_premium_config(ctx.guild.id, hash, ctx.author.id), set premium_enabled=True. Show credits = await client.get_credits(token, ctx.guild.id). Admin only check.

**Test Strategy:**

Test command availability (admin only), modal submission, token validation success/fail, DB storage, UI confirmation with credits.
