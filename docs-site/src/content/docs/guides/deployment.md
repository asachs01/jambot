---
title: Deployment Guide
description: Deploy JamBot to DigitalOcean App Platform
---

Deploy JamBot to DigitalOcean's App Platform for a managed, hassle-free hosting experience.

## Quick Deploy

[![Deploy to DO](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/sachs7/jambot/tree/main)

## Prerequisites

- A DigitalOcean account ([Sign up](https://cloud.digitalocean.com/registrations/new))
- Discord Bot Token ([Setup Guide](/setup/discord/))
- Spotify API Credentials ([Setup Guide](/setup/spotify/))

## Step-by-Step Deployment

### 1. Deploy to App Platform

**Option A: One-Click Deploy (Recommended)**

1. Click the "Deploy to DigitalOcean" button above
2. Authorize GitHub access
3. Fork or import the repository

**Option B: Manual Deployment**

1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click "Create App"
3. Select GitHub as your source
4. Choose the jambot repository
5. Select the main branch

### 2. Configure Environment Variables

Add these secrets:

| Variable | Description |
|----------|-------------|
| `DISCORD_BOT_TOKEN` | Your Discord bot token |
| `SPOTIFY_CLIENT_ID` | Your Spotify client ID |
| `SPOTIFY_CLIENT_SECRET` | Your Spotify client secret |

### 3. Deploy the App

1. Review the configuration
2. Click "Create Resources"
3. Wait 2-3 minutes for deployment
4. Note your app URL: `https://jambot-xxxxx.ondigitalocean.app`

### 4. Complete Spotify Setup

**Update Spotify Redirect URI:**

1. Go to your [Spotify App Dashboard](https://developer.spotify.com/dashboard)
2. Click "Edit Settings"
3. Add redirect URI: `https://your-app-url.ondigitalocean.app/callback`
4. Save changes

**Authenticate with Spotify:**

1. Visit your app URL
2. Click "Connect with Spotify"
3. Authorize the app

### 5. Configure in Discord

1. Add the bot to your server
2. Run `/jambot-setup` to configure jam leaders and approvers
3. Run `/jambot-spotify-setup` if not already authenticated

### 6. Test the Bot

Post a test setlist:

```
Here's the setlist for tonight's jam:

Will the Circle (G)
Little Georgia Rose (A)
Wabash Cannonball (G)
```

The bot should detect it and start the approval workflow.

## Costs

### App Platform Pricing

- **Basic Plan**: $5/month
  - 512 MB RAM
  - 1 vCPU
  - Perfect for small to medium servers

- **Professional Plan**: Starting at $12/month
  - More resources for larger servers

### Database Storage

SQLite is stored in the container filesystem:
- ✅ Free (included with your app)
- ✅ Data persists between deploys
- ⚠️ Destroying the app deletes data

## Monitoring

### View Logs

1. Go to your app in App Platform
2. Click on the jambot service
3. Click "Runtime Logs"

### Health Checks

App Platform monitors your app at:
```
https://your-app-url.ondigitalocean.app/health
```

Failed health checks trigger automatic restarts.

## Updating

### Automatic Updates

With "Auto-Deploy" enabled, pushing to GitHub triggers automatic deployment.

### Manual Updates

1. Go to App Platform console
2. Click "Deploy" → "Deploy latest commit"

## Advanced Configuration

### Custom Domain

1. Go to app Settings → Domains
2. Add your custom domain
3. Update DNS records
4. Update Spotify redirect URI

### Scaling

For more traffic:
1. Change instance size to Professional
2. Increase instance count for high availability

## Troubleshooting

### Bot Shows Offline

- Check runtime logs for errors
- Verify `DISCORD_BOT_TOKEN` is correct
- Ensure app is running

### Spotify Authentication Fails

- Verify redirect URI matches in Spotify dashboard
- Check client ID and secret
- Visit `/` to see authentication status

### Build Failures

- Check all environment variables are set
- Verify Dockerfile is valid
- Review build logs

## Alternative Deployment Options

- **Droplet + Docker**: Full persistence, $6/month
- **App Platform + Managed DB**: Production-ready, $20/month
- **Self-hosted**: Free, your own server
