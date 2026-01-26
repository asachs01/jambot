# Task ID: 38

**Title:** Implement Stripe Checkout Session Creation

**Status:** cancelled

**Dependencies:** 33 ✗, 37 ✗

**Priority:** high

**Description:** Create POST /api/v1/checkout endpoint generating Stripe Checkout URLs.

**Details:**

Auth required. Get tenant.stripe_customer_id or stripe.Customer.create(email=f'{guild_name} Premium'). Create session: stripe.checkout.Session.create(customer=customer_id, payment_method_types=['card'], line_items=[{'price': product.stripe_price_id, 'quantity':1}], mode='payment', metadata={'guild_id': guild_id, 'product_id': product_id}, success_url, cancel_url). Return session.url.

**Test Strategy:**

Mock Stripe, test session creation with/without existing customer, verify metadata includes guild_id, URL returned.
