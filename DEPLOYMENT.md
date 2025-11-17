# Deployment Guide - DigitalOcean Container App

This guide explains how to deploy Jambot to DigitalOcean's Container App platform.

## Prerequisites

- DigitalOcean account
- `doctl` CLI tool installed ([Installation Guide](https://docs.digitalocean.com/reference/doctl/how-to/install/))
- Docker installed locally
- Completed [Discord](SETUP_DISCORD.md) and [Spotify](SPOTIFY_SETUP.md) setup

## Overview

DigitalOcean Container Apps provide:
- Managed container hosting
- Automatic HTTPS and load balancing
- Built-in monitoring and logs
- Persistent volume support (for SQLite database)
- Resource limits and scaling

## Step 1: Install and Configure doctl

1. Install doctl:
```bash
# macOS
brew install doctl

# Linux
cd ~
wget https://github.com/digitalocean/doctl/releases/download/v1.94.0/doctl-1.94.0-linux-amd64.tar.gz
tar xf ~/doctl-1.94.0-linux-amd64.tar.gz
sudo mv ~/doctl /usr/local/bin
```

2. Authenticate:
```bash
doctl auth init
```

Follow the prompts to enter your DigitalOcean API token.

## Step 2: Create Container Registry

1. Create a registry:
```bash
doctl registry create jambot-registry
```

2. Log in to the registry:
```bash
doctl registry login
```

## Step 3: Build and Push Docker Image

1. Build the image:
```bash
docker build -t jambot:latest .
```

2. Tag the image for your registry:
```bash
# Get your registry name
doctl registry get

# Tag the image (replace YOUR_REGISTRY with your registry name)
docker tag jambot:latest registry.digitalocean.com/YOUR_REGISTRY/jambot:latest
```

3. Push to DigitalOcean Container Registry:
```bash
docker push registry.digitalocean.com/YOUR_REGISTRY/jambot:latest
```

## Step 4: Deploy Using DigitalOcean Console (Recommended)

The easiest way to deploy is through the DigitalOcean web console:

1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click **"Create App"**
3. Choose **"DigitalOcean Container Registry"**
4. Select your registry and the `jambot` repository
5. Choose **"Worker"** as the resource type (not Web Service - Discord bots don't need HTTP)
6. Configure:
   - **Name**: jambot
   - **Instance Size**: Basic (512 MB RAM, $5/mo)
   - **Instance Count**: 1
7. Add environment variables (see Step 6)
8. Click **"Next"** → **"Create Resources"**

### Alternative: Deploy Using app.yaml

If you prefer CLI deployment, use the included `app.yaml`:

```bash
doctl apps create --spec app.yaml
```

**Note**: The `app.yaml` file is already included in your project root.

## Step 5: Configure Persistent Storage

⚠️ **Important**: App Platform workers currently have limited persistent volume support. For production use, consider these options:

### Option A: Use Managed Database (Recommended for Production)

Instead of SQLite, use DigitalOcean Managed PostgreSQL:
1. Create a managed PostgreSQL database in DigitalOcean
2. Update the code to use PostgreSQL instead of SQLite
3. Connection info is automatically injected as environment variables

### Option B: External Storage

Use DigitalOcean Spaces (S3-compatible) to periodically backup the SQLite database:
1. App stores database in container filesystem (ephemeral)
2. Periodic backup to Spaces
3. Restore on startup

### Option C: Persistent Volume (Limited Support)

Currently, App Platform has limited support for persistent volumes on worker services. Monitor DigitalOcean's roadmap for updates.

**For this project**: The bot will work without persistence initially, but song memories will be lost on restart. Consider implementing Option A or B for production.

## Step 6: Configure Environment Variables

Set sensitive environment variables (never commit these to version control):

```bash
# Replace APP_ID with your app ID from Step 5

# Discord Configuration
doctl apps update APP_ID --set-env DISCORD_BOT_TOKEN=your_bot_token
doctl apps update APP_ID --set-env DISCORD_JAM_LEADER_ID=user_id
doctl apps update APP_ID --set-env DISCORD_ADMIN_ID=user_id

# Spotify Configuration
doctl apps update APP_ID --set-env SPOTIFY_CLIENT_ID=your_client_id
doctl apps update APP_ID --set-env SPOTIFY_CLIENT_SECRET=your_client_secret
doctl apps update APP_ID --set-env SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
doctl apps update APP_ID --set-env SPOTIFY_REFRESH_TOKEN=your_refresh_token
```

Alternatively, use the DigitalOcean web console:
1. Go to your app in the [DigitalOcean Control Panel](https://cloud.digitalocean.com/apps)
2. Click **Settings** → **Environment Variables**
3. Add each variable and value
4. Click **Save**

## Step 7: Deploy

The app should deploy automatically after environment variables are set. To manually trigger a deployment:

```bash
doctl apps create-deployment APP_ID
```

Monitor the deployment:

```bash
doctl apps list-deployments APP_ID
```

## Step 8: Verify Deployment

1. Check app status:
```bash
doctl apps get APP_ID
```

2. View logs:
```bash
doctl apps logs APP_ID --follow
```

3. Verify in Discord:
   - Bot should appear online in your server
   - Check logs for any errors

## Monitoring and Maintenance

### View Logs

Real-time logs:
```bash
doctl apps logs APP_ID --follow --type RUN
```

Recent logs:
```bash
doctl apps logs APP_ID --tail 100
```

### View Metrics

In the DigitalOcean Control Panel:
1. Go to your app
2. Click **Insights** tab
3. View CPU, Memory, and Network usage

### Restart the App

```bash
doctl apps update APP_ID --redeploy
```

### Update Environment Variables

```bash
doctl apps update APP_ID --set-env VARIABLE_NAME=new_value
```

### Scale Resources

Edit `app.yaml` and update:
- `instance_count`: Number of instances (1-20)
- `instance_size_slug`: Size tier
  - `basic-xxs`: 512MB RAM, 0.5 vCPU ($5/month)
  - `basic-xs`: 1GB RAM, 1 vCPU ($10/month)
  - `basic-s`: 2GB RAM, 1 vCPU ($20/month)

Then update the app:
```bash
doctl apps update APP_ID --spec app.yaml
```

## Database Backup and Restore

### Backup Database

The SQLite database is stored in the persistent volume at `/app/data/jambot.db`.

Option 1: Using doctl (if SSH access is available):
```bash
# Connect to container
doctl apps exec APP_ID --component jambot

# Copy database to your local machine
doctl apps copy APP_ID:/app/data/jambot.db ./backup/jambot-$(date +%Y%m%d).db
```

Option 2: Via volume snapshot:
1. In the DigitalOcean Control Panel, go to **Volumes**
2. Find `jambot-data` volume
3. Click **Snapshots** → **Take Snapshot**

### Restore Database

Option 1: Upload new database:
```bash
doctl apps copy ./backup/jambot.db APP_ID:/app/data/jambot.db
doctl apps update APP_ID --redeploy
```

Option 2: From volume snapshot:
1. Create new volume from snapshot
2. Update `app.yaml` to use new volume
3. Deploy updated spec

## Updating the Bot

1. Make code changes locally
2. Build new image:
```bash
docker build -t jambot:latest .
```

3. Tag with new version:
```bash
docker tag jambot:latest registry.digitalocean.com/YOUR_REGISTRY/jambot:v1.1
docker tag jambot:latest registry.digitalocean.com/YOUR_REGISTRY/jambot:latest
```

4. Push to registry:
```bash
docker push registry.digitalocean.com/YOUR_REGISTRY/jambot:v1.1
docker push registry.digitalocean.com/YOUR_REGISTRY/jambot:latest
```

5. Trigger deployment:
```bash
doctl apps create-deployment APP_ID
```

## Troubleshooting

### App won't start

1. Check logs:
```bash
doctl apps logs APP_ID --tail 100
```

2. Common issues:
   - Missing environment variables
   - Invalid Discord/Spotify credentials
   - Database permission errors

### Database not persisting

1. Verify volume is attached:
```bash
doctl apps get APP_ID
```

2. Check volume mount path matches `DATABASE_PATH` in environment

3. Verify volume size is sufficient:
```bash
doctl compute volume list
```

### High resource usage

1. Check metrics in DigitalOcean Console
2. Review logs for errors or excessive API calls
3. Consider upgrading instance size

### Bot appears offline

1. Check logs for authentication errors
2. Verify `DISCORD_BOT_TOKEN` is correct
3. Ensure network connectivity (check app status)

### Playlist creation fails

1. Check Spotify API credentials
2. Verify refresh token is valid
3. Review logs for specific API errors

## Cost Estimation

With default configuration:
- **Basic XXS instance**: $5/month (512MB RAM, 0.5 vCPU)
- **Persistent volume (1GB)**: $0.10/month
- **Container registry storage**: ~$0.02/month

**Total**: ~$5.12/month

For higher traffic:
- Basic XS ($10/month): 1GB RAM, 1 vCPU
- Consider multiple instances for high availability

## Security Best Practices

1. **Use secrets management**:
   - Store sensitive values in DigitalOcean App Platform environment variables
   - Never commit credentials to version control

2. **Regular updates**:
   - Keep dependencies updated
   - Rebuild images periodically for security patches

3. **Monitor logs**:
   - Set up log alerts for errors
   - Review logs weekly for suspicious activity

4. **Backup database**:
   - Schedule regular automated backups
   - Test restore procedures

5. **Resource limits**:
   - Set appropriate CPU/memory limits
   - Monitor usage and adjust as needed

## Alternative Deployment Options

### Docker Compose (Self-Hosted)

```bash
docker-compose up -d
```

See `docker-compose.yml` for configuration.

### Other Cloud Platforms

The bot can also be deployed to:
- **AWS ECS/Fargate**: Use ECS task definition with EFS for database
- **Google Cloud Run**: Mount Cloud Storage bucket for database
- **Azure Container Instances**: Use Azure Files for persistent storage
- **Heroku**: Use Heroku Postgres instead of SQLite

## Next Steps

- [Review admin workflow](ADMIN_GUIDE.md)
- [Check troubleshooting guide](TROUBLESHOOTING.md)
- [Set up monitoring and alerts](#monitoring-and-maintenance)

## Support Resources

- [DigitalOcean App Platform Documentation](https://docs.digitalocean.com/products/app-platform/)
- [doctl Reference](https://docs.digitalocean.com/reference/doctl/)
- [DigitalOcean Community](https://www.digitalocean.com/community/tags/app-platform)
