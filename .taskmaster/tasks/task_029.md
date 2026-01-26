# Task ID: 29

**Title:** Implement Credits and Buy Commands

**Status:** pending

**Dependencies:** 27, 28

**Priority:** medium

**Description:** Add /jambot-credits and /jambot-buy-credits commands with credit display and checkout links.

**Details:**

/jambot-credits: if premium_enabled, client.get_credits(), embed with balance/trial/purchased, low balance shows buy button. /jambot-buy-credits: View with buttons for 10/25/50 packs, callback generates client.get_checkout_url('10pack'), ephemeral response with URL.

**Test Strategy:**

Test commands hidden when not premium_enabled, credits display accurate, buy buttons generate valid URLs, low balance messaging.
