# JamBot Premium Chord Chart Service - Product Requirements Document

## Overview

Monetize AI chord chart generation via a closed-source premium API service, keeping the core JamBot bot open source. Uses Stripe for per-server credit pack purchases.

## Business Model

### Feature Comparison

| Feature | Free (Open Source) | Premium |
|---------|-------------------|---------|
| Playlist generation | Yes | Yes |
| View existing charts | Yes | Yes |
| Create/AI generate charts | No | Yes |
| Free trial | - | 5 generations |

### Credit Packs (Per-Server)
- **10 credits**: $4.99 (~$0.50/chart)
- **25 credits**: $9.99 (~$0.40/chart, 17% savings)
- **50 credits**: $17.99 (~$0.36/chart, 28% savings)

---

## Phase 1: Premium API Service Foundation

### Task: Create Premium API Repository Structure

Create a new repository `jambot-premium-api` with FastAPI-based architecture for hosting the closed-source premium service.

**Requirements:**
- Initialize FastAPI project structure with proper Python packaging
- Set up Poetry or pip for dependency management
- Configure environment variables for:
  - PostgreSQL connection
  - OpenRouter API key
  - Stripe API keys (test and live)
- Create Docker and docker-compose configuration for local development
- Set up GitHub repository with proper .gitignore

**Files to create:**
- `jambot-premium-api/pyproject.toml` or `requirements.txt`
- `jambot-premium-api/src/main.py` - FastAPI app entry point
- `jambot-premium-api/src/config.py` - Configuration management
- `jambot-premium-api/Dockerfile`
- `jambot-premium-api/docker-compose.yml`
- `jambot-premium-api/.env.example`

---

### Task: Design and Implement Premium API Database Schema

Create PostgreSQL schema for the premium service including tenant management, credits, transactions, and generation history.

**Tables to create:**

1. **tenants** - API key management
   - `id` UUID PRIMARY KEY
   - `discord_guild_id` BIGINT UNIQUE NOT NULL
   - `guild_name` VARCHAR(255)
   - `api_token_hash` VARCHAR(72) NOT NULL (bcrypt)
   - `api_token_prefix` VARCHAR(8) NOT NULL (fast lookup)
   - `stripe_customer_id` VARCHAR(255)
   - `created_at` TIMESTAMP
   - `is_active` BOOLEAN

2. **credits** - Credit balances
   - `id` SERIAL PRIMARY KEY
   - `tenant_id` UUID REFERENCES tenants(id)
   - `balance` INTEGER DEFAULT 5 (free trial)
   - `trial_used` INTEGER DEFAULT 0
   - `lifetime_purchased` INTEGER DEFAULT 0
   - `updated_at` TIMESTAMP

3. **credit_transactions** - Audit trail
   - `id` SERIAL PRIMARY KEY
   - `tenant_id` UUID REFERENCES tenants(id)
   - `transaction_type` VARCHAR(20) (purchase, usage, refund)
   - `amount` INTEGER NOT NULL
   - `balance_after` INTEGER NOT NULL
   - `stripe_payment_id` VARCHAR(255)
   - `generation_id` UUID
   - `created_at` TIMESTAMP

4. **generation_history** - Generation tracking
   - `id` UUID PRIMARY KEY
   - `tenant_id` UUID REFERENCES tenants(id)
   - `guild_id` BIGINT NOT NULL
   - `request_title` VARCHAR(255)
   - `model_used` VARCHAR(100)
   - `prompt_tokens` INTEGER
   - `completion_tokens` INTEGER
   - `estimated_cost_usd` DECIMAL(10, 6)
   - `latency_ms` INTEGER
   - `success` BOOLEAN
   - `created_at` TIMESTAMP

5. **products** - Stripe product configuration
   - `id` VARCHAR(50) PRIMARY KEY
   - `stripe_product_id` VARCHAR(255)
   - `stripe_price_id` VARCHAR(255)
   - `credits` INTEGER NOT NULL
   - `price_cents` INTEGER NOT NULL
   - `is_active` BOOLEAN

**Requirements:**
- Create Alembic migration scripts
- Add proper indexes for performance
- Create database connection pooling

---

### Task: Implement API Token Generation and Validation

Create secure API token management for tenant authentication.

**Requirements:**
- Generate cryptographically secure tokens (32 bytes, base64 encoded)
- Store bcrypt hash of tokens in database
- Store 8-character prefix for fast lookup
- Implement `validate_token(token)` function
- Token format: `jbp_{prefix}_{secret}` (e.g., `jbp_abc12345_xxxxx...`)
- Rate limiting by token

**Endpoints:**
- `POST /api/v1/tokens/generate` - Generate new token for guild (internal only)
- `POST /api/v1/validate` - Validate token and return tenant info

---

### Task: Implement Credit Management System

Create the credit balance tracking and transaction logging system.

**Requirements:**
- Atomic credit deduction with database transactions
- Transaction logging for all credit changes
- Support for:
  - Trial credits (max 5 per tenant)
  - Purchased credits
  - Credit balance queries
- Implement credit check before generation

**Functions:**
- `get_balance(tenant_id)` - Return current credit balance
- `deduct_credit(tenant_id, generation_id)` - Atomic deduction with transaction log
- `add_credits(tenant_id, amount, stripe_payment_id)` - Add purchased credits
- `get_trial_remaining(tenant_id)` - Check remaining trial credits

---

### Task: Implement AI Chord Chart Generation Endpoint

Create the core generation endpoint that uses OpenRouter to generate chord charts.

**Endpoint:** `POST /api/v1/generate`

**Request:**
```json
{
  "title": "Mountain Dew",
  "artist": "Stanley Brothers",
  "key": "G",
  "guild_id": 123456789
}
```

**Response (success):**
```json
{
  "success": true,
  "chart": {
    "title": "Mountain Dew",
    "key": "G",
    "sections": [...],
    "lyrics": "..."
  },
  "credits_remaining": 7,
  "generation_id": "uuid"
}
```

**Response (insufficient credits):**
```json
{
  "success": false,
  "error": "insufficient_credits",
  "credits_remaining": 0,
  "purchase_url": "https://premium.jambot.io/buy"
}
```

**Requirements:**
- Validate API token from Authorization header
- Check credit balance before generation
- Call OpenRouter API with DeepSeek V3 model
- Parse LLM response into structured chart format
- Log generation in generation_history table
- Deduct credit only on successful generation
- Return structured chart data

---

### Task: Implement Credits Query Endpoint

Create endpoint to check credit balance.

**Endpoint:** `GET /api/v1/credits`

**Headers:** `Authorization: Bearer {token}`

**Response:**
```json
{
  "credits_remaining": 7,
  "trial_credits_remaining": 2,
  "lifetime_purchased": 10
}
```

---

## Phase 2: Stripe Integration

### Task: Set Up Stripe Products and Prices

Configure Stripe account with credit pack products.

**Products to create:**
1. JamBot Credits - 10 Pack
   - Price: $4.99
   - Metadata: `credits: 10`

2. JamBot Credits - 25 Pack
   - Price: $9.99
   - Metadata: `credits: 25`

3. JamBot Credits - 50 Pack
   - Price: $17.99
   - Metadata: `credits: 50`

**Requirements:**
- Create products in Stripe Dashboard (test mode first)
- Store product/price IDs in products table
- Document product IDs in configuration

---

### Task: Implement Stripe Checkout Session Creation

Create endpoint to generate Stripe Checkout sessions for credit purchases.

**Endpoint:** `POST /api/v1/checkout`

**Request:**
```json
{
  "product_id": "credit_pack_25",
  "guild_id": 123456789,
  "success_url": "https://premium.jambot.io/success",
  "cancel_url": "https://premium.jambot.io/cancel"
}
```

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/..."
}
```

**Requirements:**
- Validate API token
- Create/retrieve Stripe customer for tenant
- Create Checkout Session with product
- Include guild_id in session metadata for webhook processing
- Return checkout URL

---

### Task: Implement Stripe Webhook Handler

Create webhook endpoint to process Stripe events and add credits.

**Endpoint:** `POST /webhook/stripe`

**Events to handle:**
- `checkout.session.completed` - Add credits to tenant balance

**Requirements:**
- Verify webhook signature with Stripe secret
- Extract tenant from session metadata (guild_id)
- Look up product to determine credit amount
- Add credits with transaction logging
- Handle idempotency (prevent double-crediting)
- Return 200 on success, appropriate error codes on failure

---

## Phase 3: Bot Integration

### Task: Add Premium Configuration to Bot Database

Extend JamBot's bot_configuration table for premium features.

**Schema changes:**
```sql
ALTER TABLE bot_configuration ADD COLUMN premium_api_token_hash VARCHAR(72);
ALTER TABLE bot_configuration ADD COLUMN premium_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE bot_configuration ADD COLUMN premium_setup_by BIGINT;
ALTER TABLE bot_configuration ADD COLUMN premium_setup_at TIMESTAMP;
```

**New database methods:**
- `save_premium_config(guild_id, token_hash, setup_by)` - Store premium configuration
- `get_premium_config(guild_id)` - Retrieve premium configuration
- `is_premium_enabled(guild_id)` - Quick check for premium status

---

### Task: Create Premium API HTTP Client

Create `src/premium_client.py` for communicating with the premium API.

**Class:** `PremiumClient`

**Methods:**
- `__init__(base_url, timeout=30)` - Initialize client
- `validate_token(token)` - Validate token with premium API
- `get_credits(token, guild_id)` - Get current credit balance
- `generate_chart(token, guild_id, title, artist=None, key=None)` - Generate chart via API
- `get_checkout_url(token, product_id, guild_id)` - Get Stripe checkout URL

**Requirements:**
- Use aiohttp for async HTTP requests
- Proper error handling and retries
- Timeout configuration
- Response parsing and error mapping

---

### Task: Implement Premium Setup Modal and Command

Add `/jambot-premium-setup` command for configuring premium access.

**Modal:** `PremiumSetupModal`
- Field: API Token (password field for security)

**Command:** `/jambot-premium-setup`
- Admin only (requires ADMINISTRATOR permission)
- Opens modal for token entry
- Validates token against premium API
- Stores hashed token in bot_configuration
- Sets premium_enabled = True on success
- Shows confirmation with credit balance

---

### Task: Implement Credits and Buy Commands

Add commands for checking credits and purchasing more.

**Command:** `/jambot-credits`
- Check if premium is enabled for guild
- Query credit balance from premium API
- Display balance with usage info
- Show purchase link if balance is low

**Command:** `/jambot-buy-credits`
- Check if premium is enabled
- Show credit pack options with prices
- Generate checkout URL via premium API
- Return Stripe checkout link

**UI Components:**
- Credit pack selection buttons (10, 25, 50 packs)
- Ephemeral response with checkout URL

---

### Task: Add Premium Gating to Chart Creation

Modify `/jambot-chart create` to check premium status before allowing generation.

**Flow:**
1. User invokes `/jambot-chart create`
2. Check `premium_enabled` for guild
3. If not enabled:
   - Show message: "Premium required for chart creation"
   - Include info about 5 free trial generations
   - Prompt to use `/jambot-premium-setup`
4. If enabled:
   - Check credit balance via premium API
   - If credits > 0: Proceed with generation via premium API
   - If credits = 0: Show "No credits remaining" with purchase link
5. On successful generation:
   - Store chart in local database for free future viewing
   - Show remaining credits
   - Send PDF

**Requirements:**
- Modify `ChartCommands.handle_chart_create()`
- Add premium check before showing modal
- Call premium API for generation instead of local
- Store generated chart locally

---

### Task: Add Premium Configuration to Config Module

Update `src/config.py` with premium API settings.

**New configuration:**
```python
# Premium API Configuration
PREMIUM_API_BASE_URL: str = os.getenv("PREMIUM_API_BASE_URL", "https://api.premium.jambot.io")
PREMIUM_API_TIMEOUT: int = int(os.getenv("PREMIUM_API_TIMEOUT", "60"))
```

**Requirements:**
- Add to Config class
- Document in .env.example
- Make base URL configurable for testing

---

## Phase 4: Documentation and Polish

### Task: Update Bot Documentation for Premium Features

Update documentation to explain premium features.

**Files to update:**
- `docs/configuration.html` - Add premium setup section
- `docs/admin-guide.html` - Add premium management guide
- `CONFIGURATION.md` - Add premium environment variables
- `README.md` - Add premium features section

**Documentation to add:**
- How to set up premium access
- Credit system explanation
- Troubleshooting premium issues

---

### Task: Create Premium API Documentation

Create documentation for the premium API (for internal use and potential partners).

**Documentation to create:**
- API endpoint reference
- Authentication guide
- Webhook integration guide
- Error codes reference

---

### Task: Add Premium Feature Tests

Create tests for premium functionality.

**Bot-side tests:**
- Test premium client HTTP calls (mocked)
- Test premium gating logic
- Test premium setup command flow

**API-side tests:**
- Test token generation and validation
- Test credit management
- Test generation endpoint
- Test Stripe webhook handling

---

### Task: Deploy Premium API Service

Deploy the premium API to production.

**Requirements:**
- Set up DigitalOcean droplet or app
- Configure PostgreSQL database
- Set up environment variables
- Configure SSL certificate
- Set up Stripe webhook endpoint
- Configure monitoring and logging

---

### Task: End-to-End Testing and Launch

Perform comprehensive testing before launch.

**Test scenarios:**
1. Free flow: `/jambot-chart view` works without premium
2. Gating: `/jambot-chart create` blocked without token
3. Trial: New server gets 5 free generations
4. Purchase: Stripe checkout adds credits
5. Generation: AI chart created and stored locally
6. Metering: Credits deducted on success only

**Launch checklist:**
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Stripe in live mode
- [ ] Monitoring configured
- [ ] Support process defined
