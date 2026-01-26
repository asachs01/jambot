# Task ID: 21

**Title:** Implement AI Chord Chart Generation Endpoint

**Status:** pending

**Dependencies:** 19, 20

**Priority:** high

**Description:** Create POST /api/v1/generate endpoint with token validation, credit check, OpenRouter DeepSeek V3 call, structured response.

**Details:**

Extract token from Authorization: Bearer, validate_token(), check_credits()>0, deduct_credit(). POST to OpenRouter /api/v1/chat/completions with model='deepseek/deepseek-chat-v3', parse response to chart.sections/lyrics structure. Log to generation_history (tokens from usage, latency=time.perf_counter()). Return chart or insufficient_credits with purchase_url.

**Test Strategy:**

Mock OpenRouter/stripe, test success flow deducts credit, insufficient returns error, invalid token 401, parse malformed LLM response gracefully.
