# Jambot - Bluegrass Jam Setlist to Spotify Playlist Bot

A Discord bot that automatically converts bluegrass jam setlists posted by a jam leader into curated Spotify playlists. The bot monitors Discord messages, extracts song titles, finds them on Spotify, validates selections through an admin approval workflow, and creates shareable Spotify playlists.

## Features

- **Automatic Setlist Detection**: Monitors messages from a configured jam leader and detects setlist patterns
- **Smart Song Matching**: Searches Spotify with intelligent fuzzy matching for common bluegrass song variations
- **Song Version Memory**: Remembers approved song versions across multiple jams for consistency
- **Admin Approval Workflow**: DM-based validation system with emoji reactions for song selection
- **Manual Overrides**: Support for manual song replacement via commands
- **Persistent Storage**: SQLite database for song history and setlist tracking
- **Container-Ready**: Docker support for easy deployment to DigitalOcean Container App

## Quick Start

### Prerequisites

- Python 3.11+
- Discord Bot Token ([Setup Guide](SETUP_DISCORD.md))
- Spotify API Credentials ([Setup Guide](SETUP_SPOTIFY.md))
- Docker (optional, for containerized deployment)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd jambot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. Run the bot:
```bash
python -m src.main
```

### Docker Deployment (Local or Self-Hosted)

1. Build and run the container:
```bash
docker-compose up -d
```

2. View logs:
```bash
docker-compose logs -f jambot
```

### Cloud Deployment

**DigitalOcean App Platform** (Recommended for quick start):
- See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step instructions
- Deploy as a Worker service (~$5/month)
- Note: Worker services have limited persistent storage

**Need Persistent Storage?**
- See [DEPLOYMENT_OPTIONS.md](DEPLOYMENT_OPTIONS.md) for comparison of:
  - App Platform Worker (easiest, no persistence)
  - Droplet + Docker (full persistence, $6/month)
  - App Platform + Managed DB (production-ready, $20/month)
  - Self-hosted (free, your own server)

## Configuration

All configuration is done via environment variables in `.env`:

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_BOT_TOKEN` | Discord bot authentication token | ✅ |
| `DISCORD_JAM_LEADER_ID` | User ID who posts setlists | ✅ |
| `DISCORD_ADMIN_ID` | User ID for approval workflow | ✅ |
| `SPOTIFY_CLIENT_ID` | Spotify app client ID | ✅ |
| `SPOTIFY_CLIENT_SECRET` | Spotify app client secret | ✅ |
| `SPOTIFY_REDIRECT_URI` | OAuth redirect URI | ✅ |
| `SPOTIFY_REFRESH_TOKEN` | Spotify refresh token | ✅ |
| `DATABASE_PATH` | SQLite database file path | ❌ (default: `/app/data/jambot.db`) |
| `LOG_LEVEL` | Logging level (INFO, DEBUG, etc.) | ❌ (default: `INFO`) |
| `LOG_FILE` | Log file path | ❌ (default: `/app/logs/jambot.log`) |

## How It Works

### 1. Setlist Detection

The bot monitors messages from the configured jam leader matching this pattern:
```
Here's the upcoming setlist for the [TIME] jam on [DATE]. If you want to sing any of these, please let me know or comment below.

1. Song Name (Key)
2. Song Name (Key)
...
```

### 2. Song Matching

For each song:
- First checks the database for previously approved versions
- If not found, searches Spotify with exact title
- Falls back to common bluegrass variations if needed
- Returns up to 3 matches per song

### 3. Admin Validation

The bot sends a DM to the admin with:
- **Stored versions** (✅ pre-approved)
- **Single matches** (✅ for confirmation)
- **Multiple matches** (1️⃣ 2️⃣ 3️⃣ to select)
- **No matches** (❌ reply with Spotify link)

### 4. Playlist Creation

After admin approval:
- Creates Spotify playlist named "Bluegrass Jam [DATE]"
- Adds all approved tracks in setlist order
- Posts playlist link to the original Discord channel
- Stores playlist and song data in database

## Manual Song Management

Replace a song in an approved setlist:
```
@jambot use this version of Will the Circle Be Unbroken for 11/18/2024 https://open.spotify.com/track/abc123
```

This updates both the pending setlist and the stored version for future jams.

## Database Schema

### songs
- Stores approved Spotify tracks with usage dates
- Fields: id, song_title, spotify_track_id, spotify_track_name, artist, album, spotify_url, first_used, last_used

### setlists
- Tracks created playlists
- Fields: id, date, time, playlist_name, spotify_playlist_id, spotify_playlist_url, created_at

### setlist_songs
- Links songs to setlists with position
- Fields: id, setlist_id, song_id, position

## Project Structure

```
jambot/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration management
│   ├── logger.py            # Logging setup
│   ├── database.py          # SQLite database interface
│   ├── spotify_client.py    # Spotify API integration
│   ├── setlist_parser.py    # Message parsing
│   └── bot.py               # Discord bot logic
├── data/                    # SQLite database (mounted volume)
├── logs/                    # Log files (mounted volume)
├── .env                     # Environment configuration
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container image definition
├── docker-compose.yml      # Local container orchestration
└── README.md               # This file
```

## Documentation

- [Discord Bot Setup](SETUP_DISCORD.md) - How to create and configure the Discord bot
- [Spotify API Setup](SETUP_SPOTIFY.md) - How to set up Spotify developer credentials
- [Deployment Guide](DEPLOYMENT.md) - DigitalOcean App Platform deployment
- [Deployment Options](DEPLOYMENT_OPTIONS.md) - Compare all deployment methods
- [Admin Guide](ADMIN_GUIDE.md) - Using the approval workflow
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=src
```

### Logging

The bot uses Python's built-in logging with:
- **Console output**: Simple format for monitoring
- **Rotating file logs**: Detailed format with 10MB rotation, 5 backup files
- **Log levels**: INFO (console) and DEBUG (file) by default

Logs are stored in `/app/logs/jambot.log` (or path specified in `LOG_FILE`).

## Error Handling

The bot includes comprehensive error handling for:
- Discord API failures and rate limits
- Spotify API failures with exponential backoff retry
- Database transaction errors with rollback
- Invalid Spotify URLs
- Missing configuration

All errors are logged and the admin is notified via DM for critical failures.

## Security

- Bot runs as non-root user in Docker container
- Database directory has restricted permissions (700)
- Parameterized SQL queries prevent injection
- Environment variables for sensitive credentials
- No hardcoded secrets

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[Your License Here]

## Support

For issues and questions:
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Review logs in `/app/logs/jambot.log`
- Open an issue on GitHub

## Acknowledgments

Built for the bluegrass jam community to make setlist management and playlist sharing easier.
