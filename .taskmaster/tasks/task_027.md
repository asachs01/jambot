# Task ID: 27

**Title:** Create Premium API HTTP Client

**Status:** pending

**Dependencies:** 26, 43

**Priority:** medium

**Description:** Implement PremiumClient class with aiohttp for async API calls: validate_token, get_credits, generate_chart, get_checkout_url.

**Details:**

class PremiumClient: async def __init__(self, base_url, timeout=30), async validate_token(token), async get_credits(token, guild_id), async generate_chart(token, guild_id, title, artist=None, key=None), async get_checkout_url(token, product_id, guild_id). Use aiohttp.ClientSession with timeout, json response parsing, error mapping (401->'invalid_token').

**Test Strategy:**

Mock aiohttp responses, test all methods return parsed data, handle timeouts/401/500 errors, retry logic on 5xx.
