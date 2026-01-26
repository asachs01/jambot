# Task ID: 19

**Title:** Implement API Token Generation and Validation

**Status:** pending

**Dependencies:** 18

**Priority:** high

**Description:** Create secure token generation with bcrypt hashing, 8-char prefix lookup, and validation endpoints with rate limiting.

**Details:**

Use `secrets.token_bytes(32)` for token secret, base64url encode, prefix first 8 chars. Store bcrypt.hashpw(token.encode(), bcrypt.gensalt()). Implement `POST /api/v1/tokens/generate` (internal, returns `jbp_{prefix}_{secret}`), `POST /api/v1/validate` (lookup prefix, verify hash). Use slowapi for rate limiting (100/hour per IP).

**Test Strategy:**

Generate token, validate succeeds, invalid token fails, prefix lookup <1ms, rate limit triggers after 100 calls, bcrypt hash verifies correctly.
