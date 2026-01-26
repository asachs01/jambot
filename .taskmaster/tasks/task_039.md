# Task ID: 39

**Title:** Implement Stripe Webhook Handler

**Status:** cancelled

**Dependencies:** 34 ✗, 37 ✗, 38 ✗

**Priority:** high

**Description:** Create POST /webhook/stripe endpoint processing checkout.completed events.

**Details:**

Use stripe.Webhook.construct_event(payload, sig_header, webhook_secret). If 'checkout.session.completed': guild_id=session.metadata.guild_id, product_id=session.metadata.product_id, get credits from products, stripe.Customer.retrieve(session.customer).description for tenant lookup, call add_credits(tenant_id, credits, session.payment_intent). Idempotency: check if stripe_payment_id exists in credit_transactions.

**Test Strategy:**

Use Stripe CLI forward webhook, test signature verification, credit addition, idempotency (duplicate events), error handling.
