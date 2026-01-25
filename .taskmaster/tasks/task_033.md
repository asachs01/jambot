# Task ID: 33

**Title:** Implement API Token Generation and Validation

**Status:** cancelled

**Dependencies:** 32 ✗

**Priority:** high

**Description:** Create secure token generation and validation system with bcrypt hashing and prefix lookup.

**Details:**

In `src/auth.py`: def generate_token() -> str: secret = base64.urlsafe_b64encode(os.urandom(32)).decode(), prefix = secret[:8], hash = bcrypt.hashpw(secret.encode(), bcrypt.gensalt()).decode(), store both. Token format: f'jbp_{prefix}_{secret}'. validate_token(token): extract prefix/hash, query DB by prefix, verify bcrypt.checkpw(secret.encode(), stored_hash). Endpoints: POST /api/v1/tokens/generate (internal, returns token), POST /api/v1/validate (returns tenant info). Use fastapi.Depends() for auth.

**Test Strategy:**

Test token generation produces valid format, DB storage/retrieval, validate_token succeeds/fails correctly, prefix lookup <1ms, rate limiting with slowapi.
