# Task ID: 17

**Title:** Create Premium API Repository Structure

**Status:** pending

**Dependencies:** None

**Priority:** high

**Description:** Initialize FastAPI project structure with Poetry dependency management, Docker configuration, and environment variables for PostgreSQL, OpenRouter, and Stripe.

**Details:**

Create `jambot-premium-api` repo with `pyproject.toml` using Poetry, `src/main.py` FastAPI app, `src/config.py` for env vars (POSTGRES_URL, OPENROUTER_API_KEY, STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY), `Dockerfile` with Python 3.12-slim, `docker-compose.yml` with postgres:16 service, `.env.example`, and `.gitignore` excluding .env and __pycache__.

**Test Strategy:**

Verify project structure exists, `poetry install` succeeds, `docker-compose up` starts services without errors, env vars load correctly from config.py.
