# Task ID: 44

**Title:** Update Bot Documentation for Premium Features

**Status:** pending

**Dependencies:** 43, 30, 28, 27

**Priority:** medium

**Description:** Update key documentation files to include comprehensive guides for premium feature setup, management, configuration variables, and overview.

**Details:**

1. **docs/configuration.html**: Add a new 'Premium Features Setup' section explaining PREMIUM_API_BASE_URL (default: https://api.jambot-premium.com) and PREMIUM_API_TIMEOUT (default: 30s) environment variables, including setup steps: copy from .env.example, validate with bot restart, and troubleshooting for common errors like invalid timeout values. Include code snippet: `PREMIUM_API_BASE_URL=https://api.jambot-premium.com` and `PREMIUM_API_TIMEOUT=30`. Reference Task 43 for config details. 2. **docs/admin-guide.html**: Create 'Premium Management Guide' section covering /jambot-premium-setup command (admin-only), modal token input process, validation flow, config storage with bcrypt hashing, enabling premium status, and displaying initial credits. Include screenshots or flow diagram of modal submission and success response. Link to premium gating in chart creation (Task 30). 3. **CONFIGURATION.md**: Add 'Premium Environment Variables' subsection under existing config docs, detailing PREMIUM_API_BASE_URL (required for API calls, str type), PREMIUM_API_TIMEOUT (int, validation for positive values), cross-referencing .env.example and src/config.py. Mention dependencies on PremiumClient (Task 27). 4. **README.md**: Insert 'Premium Features' section after core features, highlighting chart generation via premium API, credit-based usage, setup command, gating logic, and upgrade benefits. Add badge or callout: '🚀 Premium: Enhanced charts with AI generation'. Ensure all sections use consistent markdown styling, include links between files, and update any TOCs. Commit with message 'docs: add comprehensive premium features documentation'.

**Test Strategy:**

1. Verify docs/configuration.html contains 'Premium Features Setup' section with exact env var names, defaults, and code snippets matching Task 43. 2. Confirm docs/admin-guide.html has 'Premium Management Guide' with /jambot-premium-setup details, token flow, and references to Tasks 27-30. 3. Check CONFIGURATION.md 'Premium Environment Variables' subsection lists PREMIUM_API_BASE_URL and PREMIUM_API_TIMEOUT with types/validation. 4. Validate README.md 'Premium Features' section exists with overview, command mention, and links. 5. Build/test HTML files locally (if applicable), ensure no broken links between docs, search for 'premium' keyword yields all 4 files, and review for consistent terminology (e.g., 'PremiumClient', 'validate_token'). 6. Diff against previous versions to confirm only relevant additions, no regressions in existing content.
