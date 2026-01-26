# Task ID: 24

**Title:** Implement Stripe Checkout Session Creation

**Status:** pending

**Dependencies:** 19, 23

**Priority:** high

**Description:** Create POST /api/v1/checkout to generate Stripe Checkout URL with guild metadata.

**Details:**

Validate token, get tenant.stripe_customer_id or stripe.customers.create(email=f'{guild_name} Premium'), stripe.checkout.sessions.create(line_items=[{'price': product.stripe_price_id, 'quantity':1}], mode='payment', metadata={'guild_id': guild_id}, success_url/cancel_url). Return session.url.

**Test Strategy:**

Mock stripe lib, test creates customer if missing, session.url valid, metadata includes guild_id, handles invalid product_id.
