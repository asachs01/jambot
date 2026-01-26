# Task ID: 25

**Title:** Implement Stripe Webhook Handler

**Status:** pending

**Dependencies:** 20, 23

**Priority:** high

**Description:** Create POST /webhook/stripe to handle checkout.session.completed, add credits idempotently.

**Details:**

Verify signature stripe.WebhookSignature.verify_header(payload, sig_header, STRIPE_WEBHOOK_SECRET). For 'checkout.session.completed': guild_id=event.data.object.metadata.guild_id, lookup tenant, product=lookup by price_id, add_credits(amount=product.credits, stripe_payment_id=event.id). Idempotency via unique stripe_payment_id constraint.

**Test Strategy:**

Use stripe-cli to simulate webhook, verify signature passes/fails, credits added once, duplicate event ignored, invalid guild_id handled.
