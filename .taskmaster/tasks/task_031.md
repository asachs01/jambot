# Task ID: 31

**Title:** Create Premium API Repository Structure

**Status:** cancelled

**Dependencies:** None

**Priority:** high

**Description:** Initialize FastAPI project structure with Poetry, Docker, and environment configuration for the closed-source premium service.

**Details:**

Create `jambot-premium-api` repo. Use Poetry: `poetry init`, add `fastapi`, `uvicorn`, `alembic`, `psycopg2-binary`, `bcrypt`, `python-dotenv`, `stripe`, `openai`, `pydantic`. Create `src/main.py` with FastAPI app, `src/config.py` with Pydantic settings for DATABASE_URL, OPENROUTER_API_KEY, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET. Add Dockerfile with multi-stage build, docker-compose.yml with postgres:15, and .env.example. Implement .gitignore for __pycache__, .env, .venv.

**Test Strategy:**

Verify Poetry dependencies install, docker-compose up starts services without errors, FastAPI app runs on uvicorn src.main:app --reload, environment variables load correctly from config.py.
