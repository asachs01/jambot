# Task ID: 36

**Title:** Implement Credits Query Endpoint

**Status:** cancelled

**Dependencies:** 33 ✗, 34 ✗

**Priority:** medium

**Description:** Create GET /api/v1/credits endpoint returning balance breakdown.

**Details:**

Auth with Depends(), query credits table: {'credits_remaining': balance-trial_used, 'trial_credits_remaining': 5-trial_used if trial_used<5 else 0, 'lifetime_purchased': lifetime_purchased}. Use Pydantic response model.

**Test Strategy:**

Test with various balance/trial states, verify auth required, response matches exact schema.
