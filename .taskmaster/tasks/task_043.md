# Task ID: 43

**Title:** Add Premium Configuration to Bot Config Module

**Status:** pending

**Dependencies:** None

**Priority:** medium

**Description:** Update src/config.py to include PREMIUM_API_BASE_URL and PREMIUM_API_TIMEOUT environment variables in the Config class. Add documentation for these variables to .env.example.

**Details:**

1. Open src/config.py and import os or use existing environment loading mechanism (likely python-dotenv or pydantic-settings). 2. Add two new class attributes to the Config class: self.PREMIUM_API_BASE_URL = os.getenv('PREMIUM_API_BASE_URL', 'https://api.jambot-premium.com') and self.PREMIUM_API_TIMEOUT = int(os.getenv('PREMIUM_API_TIMEOUT', '30')). 3. Ensure these are properly typed (str for base_url, int/float for timeout) and include validation: raise ValueError('PREMIUM_API_TIMEOUT must be positive integer') if timeout <= 0. 4. Update any existing Config initialization to load these new fields. 5. Create or update .env.example in project root: add lines '# Premium API Configuration
PREMIUM_API_BASE_URL=https://api.jambot-premium.com
PREMIUM_API_TIMEOUT=30' with clear comments explaining usage (base_url for Premium API endpoint, timeout in seconds for HTTP requests). 6. Ensure config.py handles missing env vars gracefully with sensible defaults. 7. Add docstrings to new config fields explaining their purpose for Premium API integration.

**Test Strategy:**

1. Verify src/config.py loads PREMIUM_API_BASE_URL and PREMIUM_API_TIMEOUT from environment variables with correct defaults when unset. 2. Set PREMIUM_API_TIMEOUT to invalid values (negative, non-numeric) and confirm ValueError is raised. 3. Test Config instantiation: assert config.PREMIUM_API_BASE_URL == 'https://api.jambot-premium.com' and config.PREMIUM_API_TIMEOUT == 30 with default env. 4. Override env vars and confirm: os.environ['PREMIUM_API_TIMEOUT'] = '60'; new Config().PREMIUM_API_TIMEOUT == 60. 5. Check .env.example contains both variables with comments and example values. 6. Run bot startup to ensure no config loading errors from new fields. 7. Validate no breaking changes to existing config fields.
