# Task ID: 46

**Title:** End-to-End Testing and Launch Preparation

**Status:** pending

**Dependencies:** 17, 26, 27, 28, 29, 30, 43, 45

**Priority:** high

**Description:** Implement comprehensive end-to-end testing for all premium features across free flow, gating, trial, purchase, generation, and metering scenarios, then prepare for production launch.

**Details:**

1. Create a comprehensive test plan document covering all 6 scenarios: a) Free flow - Test /jambot-chart view succeeds without premium token; b) Gating - /jambot-chart create fails with appropriate error when no valid token; c) Trial - New server gets 5 free generations before metering kicks in; d) Purchase - Test Stripe checkout flow with test cards (use Stripe test keys, simulate 10/25/50 packs via /jambot-buy-credits); e) Generation - Successful AI chart creation via generate_chart API, stored locally in Discord; f) Metering - Verify credits deducted only on successful generation. 2. Set up test environment: Use Stripe test mode keys, create test Discord server, enable premium_config with test token. 3. Implement automated E2E tests using pytest-asyncio + discord.py test client, mocking PremiumClient where needed but testing real API calls to deployed service. 4. Manual testing checklist: Run each scenario step-by-step, capture screenshots/logs, verify database state (credits, configs). 5. Performance testing: Test concurrent chart generations (5+ simultaneous). 6. Launch checklist: Verify Task 45 deployment complete, all tests pass 100%, update .env.example with live Stripe keys instructions, create production rollout plan (canary servers first), set up monitoring alerts for credit deductions and API errors. 7. Documentation: Update README with E2E test instructions, production deployment guide, and troubleshooting for common failures. Use Stripe's recommended test cards (4000000000000002 for declines, 4242424242424242 for success) and Postman collection for API validation.

**Test Strategy:**

1. Run full automated test suite: pytest tests/e2e/test_premium_flows.py --cov, verify 100% pass rate across all 6 scenarios. 2. Manual validation in test Discord server: Test each flow end-to-end, verify embeds, buttons, API responses, credit balances pre/post. 3. Stripe testing: Use test checkout URLs from /jambot-buy-credits, confirm webhook handling adds credits, test declined cards trigger proper errors. 4. Database verification: Query bot_configuration and credits tables before/after tests, confirm trial credits auto-assigned, deductions only on success. 5. Load test: 10 concurrent /jambot-chart creates, verify no race conditions in metering. 6. Error coverage: Test invalid tokens, insufficient credits, API timeouts, network failures - verify graceful degradation and logging. 7. Production readiness: Smoke test live API endpoints post-Task 45, confirm health checks pass, Stripe webhook endpoint receives test events.
