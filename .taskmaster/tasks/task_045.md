# Task ID: 45

**Title:** Deploy Premium API Service to Production

**Status:** pending

**Dependencies:** 17, 26, 27, 28, 30, 43

**Priority:** high

**Description:** Deploy the premium API to a DigitalOcean droplet or app platform, configure PostgreSQL database, set up environment variables, SSL certificate, Stripe webhook endpoint, and monitoring/logging.

**Details:**

1. Create DigitalOcean Droplet (Ubuntu 22.04, 2GB RAM minimum) or App Platform service for the jambot-premium-api. 2. Install PostgreSQL 16: Add repo `echo 'deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main' > /etc/apt/sources.list.d/pgdg.list`, import key `wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -`, `apt update && apt install postgresql-16 postgresql-contrib`. 3. Configure PostgreSQL: Edit `/etc/postgresql/16/main/postgresql.conf` set `listen_addresses = '*'`, edit `pg_hba.conf` add `host all all 0.0.0.0/0 scram-sha-256`, create user `sudo -u postgres createuser jambot --createdb --pwprompt`, create DB `sudo -u postgres createdb --owner=jambot jambot`, `systemctl restart postgresql`. 4. Deploy app: `git clone` repo, `cd jambot-premium-api`, `poetry install --no-dev --only=main`, copy `.env` with DATABASE_URL=postgresql://jambot:<password>@localhost:5432/jambot, OPENROUTER_API_KEY, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PUBLISHABLE_KEY, set PORT=8000. 5. Run migrations: `poetry run alembic upgrade head`. 6. Start service: Create systemd service `/etc/systemd/system/jambot-premium.service` with `[Unit] Description=JamBot Premium API [Service] WorkingDirectory=/path/to/repo ExecStart=/path/to/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 2 Restart=always EnvironmentFile=/path/to/.env [Install] WantedBy=multi-user.target`, `systemctl enable --now jambot-premium`. 7. SSL: Use Certbot `apt install certbot python3-certbot-nginx`, `certbot --nginx -d api.jambot-premium.com`. 8. Stripe webhook: Verify endpoint `/stripe/webhook` accessible at https://api.jambot-premium.com/stripe/webhook, configure in Stripe dashboard with STRIPE_WEBHOOK_SECRET. 9. Monitoring: Install Prometheus Node Exporter and Grafana, or use DigitalOcean monitoring; set up logging to `/var/log/jambot-premium.log` with rotation. 10. Firewall: `ufw allow 22,80,443,5432/tcp`. Update bot config with production PREMIUM_API_BASE_URL=https://api.jambot-premium.com.

**Test Strategy:**

1. Verify droplet/app running, SSH access works. 2. `psql -U jambot -h localhost jambot` connects successfully, run `SELECT 1`. 3. `curl https://api.jambot-premium.com/health` returns 200 OK. 4. Test API endpoints: `/docs` loads Swagger UI, `/validate-token/validtoken` returns 200. 5. Stripe webhook test: Use Stripe CLI `stripe listen --forward-to https://api.jambot-premium.com/stripe/webhook` sends test event, verify logs show receipt. 6. SSL check: `openssl s_client -connect api.jambot-premium.com:443` shows valid cert. 7. Load test: `wrk -t12 -c400 -d30s https://api.jambot-premium.com/health`. 8. Check logs `journalctl -u jambot-premium -f`, confirm no errors. 9. Verify environment vars loaded: API response includes expected config (without secrets). 10. Database migration complete: Check alembic_version table exists.
