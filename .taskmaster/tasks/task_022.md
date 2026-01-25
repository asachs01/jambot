# Task ID: 22

**Title:** Implement Credits Query Endpoint

**Status:** pending

**Dependencies:** 19, 20

**Priority:** medium

**Description:** Create GET /api/v1/credits to return credits_remaining, trial_credits_remaining, lifetime_purchased.

**Details:**

Validate token, query credits table: credits_remaining=balance-trial_used (if trial_used<5 else 0), trial_remaining=max(5-trial_used,0), lifetime_purchased. Cache result 30s with Redis if added later.

**Test Strategy:**

Test with valid token returns correct breakdown, invalid token 401, trial/purchased scenarios match calculations.
