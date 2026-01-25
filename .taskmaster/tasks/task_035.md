# Task ID: 35

**Title:** Implement AI Chord Chart Generation Endpoint

**Status:** cancelled

**Dependencies:** 33 ✗, 34 ✗

**Priority:** high

**Description:** Create POST /api/v1/generate endpoint with token auth, credit check, OpenRouter integration, and structured response.

**Details:**

Use Depends(auth), check_credits(). Call OpenRouter: client = AsyncOpenAI(base_url='https://openrouter.ai/api/v1', api_key=config.OPENROUTER_API_KEY), response = await client.chat.completions.create(model='deepseek/deepseek-chat-v3', messages=[{'role':'user', 'content':f'Generate chord chart for {title} by {artist} in {key}'}]). Parse JSON response to Chart model (title, key, sections[], lyrics). Log to generation_history (tokens, cost, latency). Deduct credit on success. Return structured chart + credits_remaining.

**Test Strategy:**

Mock OpenRouter, test full flow: auth→credit check→generation→deduction→log→response. Test insufficient credits returns purchase_url. Verify structured parsing.
