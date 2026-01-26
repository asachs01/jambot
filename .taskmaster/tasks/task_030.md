# Task ID: 30

**Title:** Add Premium Gating to Chart Creation

**Status:** pending

**Dependencies:** 27, 28, 29

**Priority:** high

**Description:** Modify /jambot-chart create to check premium status, credits, route to premium API if enabled.

**Details:**

In handle_chart_create: if not is_premium_enabled(guild_id): show 'Premium required' with setup info. else: credits=await client.get_credits(), if credits>0: chart=await client.generate_chart(), store_chart_locally(chart), send PDF, show remaining. else: 'No credits' + buy link.

**Test Strategy:**

Test gating blocks non-premium, credits check routes correctly, successful generation stores chart and deducts, zero credits shows buy link.
