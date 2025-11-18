# Deploy to DigitalOcean App Platform

This guide will help you deploy Jambot to DigitalOcean's App Platform with a simple one-click setup.

## Quick Deploy

[![Deploy to DO](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/asachs01/jambot/tree/main)

## Step-by-Step Deployment

### 1. Prerequisites

- A DigitalOcean account ([Sign up here](https://cloud.digitalocean.com/registrations/new))
- Discord Bot Token ([Setup Guide](SETUP_DISCORD.md))
- Spotify API Credentials ([Setup Guide](SETUP_SPOTIFY.md))

### 2. Deploy to App Platform

#### Option A: One-Click Deploy (Recommended)

1. Click the **"Deploy to DigitalOcean"** button above
2. DigitalOcean will prompt you to authorize access to your GitHub account
3. Fork or import the repository
4. Continue to the next step

#### Option B: Manual Deployment

1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click **"Create App"**
3. Select **"GitHub"** as your source
4. Choose the `jambot` repository
5. Select the `main` branch
6. Click **"Next"**

### 3. Configure Environment Variables

On the environment variables page, add the following secrets:

| Variable | Value | Where to get it |
|----------|-------|----------------|
| `DISCORD_BOT_TOKEN` | Your Discord bot token | [Discord Developer Portal](https://discord.com/developers/applications) - see [SETUP_DISCORD.md](SETUP_DISCORD.md) |
| `SPOTIFY_CLIENT_ID` | Your Spotify client ID | [Spotify Dashboard](https://developer.spotify.com/dashboard) - see [SETUP_SPOTIFY.md](SETUP_SPOTIFY.md) |
| `SPOTIFY_CLIENT_SECRET` | Your Spotify client secret | [Spotify Dashboard](https://developer.spotify.com/dashboard) - see [SETUP_SPOTIFY.md](SETUP_SPOTIFY.md) |

**Note:** `SPOTIFY_REDIRECT_URI` and other variables are automatically configured.

### 4. Deploy the App

1. Review the configuration
2. Click **"Create Resources"**
3. Wait for the deployment to complete (2-3 minutes)
4. DigitalOcean will provide you with a public URL like: `https://jambot-xxxxx.ondigitalocean.app`

### 5. Complete Spotify Setup

#### Update Spotify Redirect URI

1. Go to your [Spotify App Dashboard](https://developer.spotify.com/dashboard)
2. Select your app
3. Click **"Edit Settings"**
4. Under **"Redirect URIs"**, add:
   ```
   https://your-app-url.ondigitalocean.app/callback
   ```
   (Replace `your-app-url` with your actual App Platform URL)
5. Click **"Save"**

#### Authenticate with Spotify

1. Visit your app URL: `https://your-app-url.ondigitalocean.app`
2. You'll see the Jambot setup page
3. Click **"Connect with Spotify"**
4. Log in to Spotify and authorize the app
5. You'll be redirected back to the setup page showing "✅ Spotify Connected!"

### 6. Add Bot to Discord Server

1. Get your bot invite URL from the [Discord Developer Portal](https://discord.com/developers/applications)
2. Or use this format:
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=274878221376&scope=bot%20applications.commands
   ```
   (Replace `YOUR_BOT_CLIENT_ID` with your actual bot's client ID)
3. Open the URL in your browser
4. Select your server
5. Click **"Authorize"**

### 7. Configure Jam Leaders and Approvers

1. In your Discord server, type: `/jambot-setup`
2. Fill in the modal with:
   - **Jam Leader User IDs**: Discord user IDs who can post setlists
   - **Song Approver User IDs**: Discord user IDs who can approve songs
   - **Playlist Channel ID** (optional): Where playlists should be posted
   - **Playlist Name Template** (optional): e.g., `"Bluegrass Jam {date}"`

**To get user IDs:**
- Use `/jambot-getid @username` command
- Or enable Developer Mode in Discord and right-click → Copy ID

### 8. Test the Bot

1. Post a test setlist in Discord:
   ```
   Here's the setlist for tonight's jam:

   Will the Circle (G)
   Little Georgia Rose (A)
   Wabash Cannonball (G)
   ```

2. The bot should:
   - Detect the setlist
   - Search for songs on Spotify
   - Send approval requests for ambiguous songs
   - Create a Spotify playlist
   - Post the playlist link in Discord

## Costs

### App Platform Pricing

- **Basic Plan**: $5/month
  - 512 MB RAM
  - 1 vCPU
  - Perfect for small to medium Discord servers

- **Professional Plan**: Starting at $12/month
  - More resources for larger servers

[View full pricing](https://www.digitalocean.com/pricing/app-platform)

### Database Storage

The app uses SQLite stored in the container's filesystem. This means:

- ✅ Free (included with your app)
- ⚠️ **Data persists between deploys** (as long as the app keeps running)
- ⚠️ **Destroying the app will delete all data**

**To preserve data:**
- Don't delete the app
- Redeploys/updates preserve data
- Only "Destroy App" removes data

## Monitoring and Logs

### View Application Logs

1. Go to your app in the [App Platform Console](https://cloud.digitalocean.com/apps)
2. Click on your **jambot** service
3. Click **"Runtime Logs"**
4. You'll see real-time logs of bot activity

### Check Web Interface

Visit your app URL to check Spotify authentication status:
```
https://your-app-url.ondigitalocean.app
```

### Health Checks

App Platform automatically monitors your app's health at:
```
https://your-app-url.ondigitalocean.app/health
```

If health checks fail, the app will automatically restart.

## Updating the Bot

### Automatic Updates

If you have "Auto-Deploy" enabled:
1. Push changes to your GitHub repository
2. App Platform automatically rebuilds and deploys
3. Zero downtime deployment

### Manual Updates

1. Go to your app in the [App Platform Console](https://cloud.digitalocean.com/apps)
2. Click **"Deploy"** → **"Deploy latest commit"**
3. Wait for the deployment to complete

## Troubleshooting

### Bot shows offline in Discord

- Check runtime logs for errors
- Verify `DISCORD_BOT_TOKEN` is correct
- Ensure the app is running (check App Platform dashboard)

### Spotify authentication not working

- Verify redirect URI matches in Spotify dashboard
- Check that `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are correct
- Visit `/` to see authentication status
- Try re-authenticating by visiting `/auth`

### Database issues

- Database is stored in `/app/data/jambot.db`
- Data persists across deploys but not app deletion
- Check logs for database connection errors

### App Platform build failures

- Check that all environment variables are set
- Verify Dockerfile is valid
- Review build logs in App Platform console

## Support

For issues with:
- **Jambot**: [GitHub Issues](https://github.com/asachs01/jambot/issues)
- **App Platform**: [DigitalOcean Support](https://www.digitalocean.com/support)
- **Discord API**: [Discord Developer Support](https://discord.com/developers/docs/intro)
- **Spotify API**: [Spotify Developer Support](https://developer.spotify.com/support)

## Advanced Configuration

### Custom Domain

1. Go to your app in App Platform
2. Click **"Settings"** → **"Domains"**
3. Add your custom domain
4. Update Spotify redirect URI to use your domain
5. Update DNS records as shown

### Scaling

To handle more traffic:
1. Go to app settings
2. Change instance size to Professional or higher
3. Increase instance count for high availability

### Environment-Specific Configuration

Create different apps for staging/production:
1. Use different GitHub branches
2. Set different environment variables
3. Use separate Discord bots and Spotify apps

## Next Steps

- [Configure Discord Bot](SETUP_DISCORD.md)
- [Set up Spotify Integration](SETUP_SPOTIFY.md)
- [Read the User Guide](README.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
