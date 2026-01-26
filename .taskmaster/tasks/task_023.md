# Task ID: 23

**Title:** Set Up Stripe Products and Prices

**Status:** pending

**Dependencies:** 18

**Priority:** high

**Description:** Create Stripe products for 10/25/50 credit packs and store in products table.

**Details:**

In Stripe dashboard (test mode): create products 'JamBot Credits - 10 Pack' ($4.99, metadata={'credits':10}), 25 Pack ($9.99,25), 50 Pack ($17.99,50). Insert into products table: id='10pack', stripe_product_id, stripe_price_id, credits=10, price_cents=499, is_active=true.

**Test Strategy:**

Verify products exist in Stripe dashboard, products table populated correctly, price/credit mapping accurate.
