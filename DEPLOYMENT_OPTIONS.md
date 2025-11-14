# Deployment Options Summary

## Overview

Jambot can be deployed in several ways. Here's a comparison to help you choose:

## Option 1: DigitalOcean App Platform (Worker) - EASIEST

**Pros:**
✅ Easiest deployment (point & click)
✅ Automatic container management
✅ Built-in monitoring and logs
✅ Auto-restart on failure
✅ Low cost ($5/month)

**Cons:**
❌ Limited persistent volume support for workers
❌ Song memories lost on restart (unless using external DB)

**Best For:** Quick deployment, testing, low-traffic jams

**Cost:** ~$5/month (Basic instance)

**Setup:**
1. Push image to DigitalOcean Container Registry
2. Create worker app via console
3. Set environment variables
4. Deploy!

See: `DEPLOYMENT.md` for detailed steps

---

## Option 2: DigitalOcean Droplet with Docker - FULL CONTROL

**Pros:**
✅ Full control over storage
✅ Persistent SQLite database with volumes
✅ Can SSH into server
✅ More flexible

**Cons:**
❌ Manual server management
❌ You handle updates and security
❌ Slightly higher cost

**Best For:** Production use, persistent storage needed

**Cost:** ~$6/month (basic droplet) + backups

**Setup:**
```bash
# On droplet
git clone <repo>
cd jambot
cp .env.example .env
# Edit .env with credentials
docker-compose up -d
```

---

## Option 3: DigitalOcean App Platform + Managed Database - PRODUCTION

**Pros:**
✅ Easy deployment like App Platform
✅ Fully persistent storage
✅ Managed database backups
✅ Production-ready

**Cons:**
❌ Higher cost (database adds $15/month minimum)
❌ Requires code changes (SQLite → PostgreSQL)

**Best For:** High-reliability production deployments

**Cost:** ~$20/month ($5 app + $15 database)

**Setup:**
1. Create managed PostgreSQL database
2. Update `database.py` to use PostgreSQL
3. Deploy app with database connection string
4. Database credentials auto-injected

---

## Option 4: Self-Hosted (Your Own Server) - FREE

**Pros:**
✅ No monthly cost
✅ Full control
✅ Can run on existing hardware

**Cons:**
❌ Need always-on server/computer
❌ Handle your own networking
❌ Manual management

**Best For:** Home servers, Raspberry Pi, existing infrastructure

**Cost:** Free (electricity only)

**Setup:**
```bash
git clone <repo>
cd jambot
cp .env.example .env
# Edit .env
docker-compose up -d

# Or without Docker:
pip install -r requirements.txt
python -m src.main
```

---

## Option 5: Other Cloud Providers

### AWS (ECS/Fargate)
- **Cost:** ~$10-15/month
- **Storage:** EFS for persistent SQLite
- **Complexity:** Medium-high
- **Best for:** AWS-heavy infrastructure

### Google Cloud (Cloud Run)
- **Cost:** ~$5-10/month (pay per use)
- **Storage:** Cloud Storage bucket + sync
- **Complexity:** Medium
- **Best for:** Google Cloud users

### Heroku
- **Cost:** $7/month (Eco dyno)
- **Storage:** Heroku Postgres required (switch from SQLite)
- **Complexity:** Low
- **Best for:** Simple deployment, Heroku users

### Railway
- **Cost:** $5-10/month
- **Storage:** Persistent volumes supported
- **Complexity:** Low
- **Best for:** Similar to App Platform

---

## Recommended Deployment Path

### 1. For Testing/Getting Started
**Use:** DigitalOcean App Platform (Worker)
- Quick to set up
- Low cost
- Good for testing the bot
- Don't worry about persistence yet

### 2. For Regular Jams (Small Scale)
**Use:** DigitalOcean Droplet with Docker
- Persistent storage works perfectly
- Still affordable
- Full control

### 3. For Production/High Reliability
**Use:** App Platform + Managed Database
- Best reliability
- Managed backups
- Automatic failover
- Worth the extra cost if this is critical

---

## Storage Persistence Comparison

| Deployment | Database Persists? | Song Memories? | Notes |
|------------|-------------------|----------------|-------|
| App Platform Worker | ❌ | ❌ | Ephemeral filesystem |
| Droplet + Docker | ✅ | ✅ | Docker volumes persist |
| App Platform + Postgres | ✅ | ✅ | Managed database |
| Self-Hosted | ✅ | ✅ | Local filesystem |

---

## My Recommendation

**Start with:** DigitalOcean App Platform Worker
- Deploy in <10 minutes
- Test all functionality
- See if you like the bot

**Upgrade to:** Droplet with Docker if you need persistence
- Simple migration
- Copy database from local testing
- $6/month is very affordable

**Consider:** Managed database only if:
- Running multiple bots
- Need guaranteed uptime
- Budget allows $20/month

---

## Quick Start Guide

### I Want the Fastest Deployment (No Persistence)

```bash
# 1. Build and push image
docker build -t jambot .
docker tag jambot registry.digitalocean.com/YOUR_REGISTRY/jambot
docker push registry.digitalocean.com/YOUR_REGISTRY/jambot

# 2. Go to cloud.digitalocean.com/apps
# 3. Create Worker app from your registry
# 4. Add environment variables
# 5. Deploy!
```

See: `DEPLOYMENT.md` Section "Quick Deploy"

### I Want Persistent Storage

```bash
# 1. Create droplet (Ubuntu 22.04)
# 2. SSH into droplet
ssh root@your_droplet_ip

# 3. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 4. Deploy bot
git clone <your_repo>
cd jambot
cp .env.example .env
nano .env  # Add your credentials
docker-compose up -d

# 5. Check logs
docker-compose logs -f
```

---

## Migration Path

If you start with App Platform and want to move to persistent storage:

1. **Export your database** (if you tested locally first):
   ```bash
   # Copy local database
   scp data/jambot.db root@droplet:/root/jambot/data/
   ```

2. **Switch deployment**:
   - Stop App Platform worker
   - Start Droplet deployment
   - Point bot token to new instance

3. **All song memories preserved!**

---

## Questions?

- See `DEPLOYMENT.md` for detailed App Platform steps
- See `docker-compose.yml` for self-hosted setup
- See `TROUBLESHOOTING.md` for common issues

## Summary

**Quick Test:** App Platform Worker (no persistence)
**Production Ready:** Droplet + Docker (with persistence)
**Enterprise:** App Platform + Managed Database
**Budget:** Self-hosted on your own server
