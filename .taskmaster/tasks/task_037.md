# Task ID: 37

**Title:** Set Up Stripe Products and Integrate with Database

**Status:** cancelled

**Dependencies:** 32 ✗

**Priority:** high

**Description:** Create Stripe products/prices and populate products table.

**Details:**

Install stripe: poetry add stripe. In Stripe Dashboard (test mode): create products 'JamBot Credits - 10 Pack' ($4.99, metadata={'credits':10}), 25 Pack ($9.99, credits:25), 50 Pack ($17.99, credits:50). Get price_ids. INSERT into products: ('credit_pack_10', stripe_product_id, stripe_price_id, 10, 499, true), etc. stripe.api_key = config.STRIPE_SECRET_KEY.

**Test Strategy:**

Verify products table populated correctly, test stripe.Price.retrieve(price_id) returns expected data, product lookup by id works.
