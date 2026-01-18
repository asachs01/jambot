"""Spotify API integration for Jambot."""
import time
from typing import List, Optional, Dict, Any
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import MemoryCacheHandler
from src.config import Config
from src.logger import logger


class SpotifyClient:
    """Wrapper for Spotify API operations with retry logic."""

    # Common bluegrass song title variations
    SONG_VARIATIONS = {
        "will the circle": ["will the circle be unbroken", "can the circle be unbroken"],
        "uncloudy day": ["unclouded day", "the uncloudy day"],
        "angel band": ["the angel band"],
        "man of constant sorrow": ["i am a man of constant sorrow"],
        "blue moon of kentucky": ["blue moon"],
        "rocky top": [],
        "foggy mountain breakdown": [],
    }

    def __init__(self, db=None, guild_id: Optional[int] = None):
        """Initialize Spotify client with OAuth.

        Args:
            db: Database instance for token storage (optional).
            guild_id: Discord guild ID for multi-guild support (optional, defaults to 0 for legacy).
        """
        logger.info(f"Initializing Spotify client for guild {guild_id}...")
        self.db = db
        self.guild_id = guild_id if guild_id is not None else 0  # 0 for legacy single-guild

        # Load Spotify credentials for this guild
        self.credentials = self._get_spotify_credentials()

        try:
            self.sp = self._authenticate()
            logger.info("Spotify authentication complete, getting user ID...")
            self.user_id = self._get_user_id()
            logger.info(f"Spotify client initialized for user: {self.user_id} (guild: {self.guild_id})")
        except Exception as e:
            logger.error(f"Failed to initialize Spotify client for guild {self.guild_id}: {e}")
            logger.warning("Spotify features will be disabled - bot will still detect setlists")
            logger.warning("To fix Spotify authentication, use /jambot-spotify-config and /jambot-spotify-setup in Discord")
            self.sp = None
            self.user_id = None

    def _get_spotify_credentials(self) -> Dict[str, str]:
        """Get Spotify app credentials from database for this guild.

        Returns:
            Dictionary with client_id, client_secret, and redirect_uri.

        Raises:
            ValueError: If no credentials configured for this guild.
        """
        if not self.db:
            from src.database import Database
            self.db = Database()

        # Get bot configuration for this guild
        config = self.db.get_bot_configuration(self.guild_id)

        if not config:
            raise ValueError(
                f"No configuration found for guild {self.guild_id}. "
                "Run /jambot-setup to configure the bot first."
            )

        # Check if Spotify credentials are configured
        client_id = config.get('spotify_client_id')
        client_secret = config.get('spotify_client_secret')
        redirect_uri = config.get('spotify_redirect_uri')

        # Fall back to environment variables for legacy/development
        if not client_id or not client_secret:
            logger.warning(
                f"No Spotify credentials configured for guild {self.guild_id}, "
                "falling back to environment variables (legacy mode)"
            )
            return {
                'client_id': Config.SPOTIFY_CLIENT_ID,
                'client_secret': Config.SPOTIFY_CLIENT_SECRET,
                'redirect_uri': Config.SPOTIFY_REDIRECT_URI,
            }

        # Use configured redirect_uri or fall back to default web server URL
        if not redirect_uri:
            redirect_uri = Config.SPOTIFY_REDIRECT_URI
            logger.info(f"Using default redirect URI: {redirect_uri}")

        logger.info(f"Loaded Spotify credentials for guild {self.guild_id}")
        return {
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
        }

    def _get_tokens_from_db(self) -> dict:
        """Get stored Spotify tokens from database for this guild.

        Returns:
            Dictionary with access_token, refresh_token, and expires_at.

        Raises:
            ValueError: If no tokens found in database for this guild.
        """
        if not self.db:
            from src.database import Database
            self.db = Database()

        with self.db.get_connection() as conn:
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT access_token, refresh_token, expires_at
                FROM spotify_tokens
                WHERE guild_id = %s
            """, (self.guild_id,))

            row = cursor.fetchone()
            if not row:
                raise ValueError(
                    f"No Spotify tokens found for guild {self.guild_id}. "
                    "Use /jambot-spotify-setup in Discord to connect Spotify"
                )

            return {
                'access_token': row['access_token'],
                'refresh_token': row['refresh_token'],
                'expires_at': row['expires_at'],
            }

    def _save_tokens_to_db(self, access_token: str, refresh_token: str, expires_at: int, user_id: Optional[int] = None):
        """Save tokens to database for this guild.

        Args:
            access_token: Spotify access token.
            refresh_token: Spotify refresh token.
            expires_at: Unix timestamp when token expires.
            user_id: Discord user ID who authorized (optional, defaults to 0 for legacy).
        """
        if not self.db:
            from src.database import Database
            self.db = Database()

        authorized_by = user_id if user_id is not None else 0

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Insert or update tokens for this guild (PostgreSQL upsert)
            cursor.execute("""
                INSERT INTO spotify_tokens
                (guild_id, access_token, refresh_token, expires_at, authorized_by, updated_at)
                VALUES (%s, %s, %s, %s, %s, EXTRACT(EPOCH FROM NOW()))
                ON CONFLICT (guild_id) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    expires_at = EXCLUDED.expires_at,
                    authorized_by = EXCLUDED.authorized_by,
                    updated_at = EXTRACT(EPOCH FROM NOW())
            """, (self.guild_id, access_token, refresh_token, expires_at, authorized_by))

            logger.info(f"Saved Spotify tokens for guild {self.guild_id} (authorized by user {authorized_by})")

    def _authenticate(self) -> spotipy.Spotify:
        """Authenticate with Spotify using database tokens.

        Returns:
            Authenticated Spotify client.

        Raises:
            ValueError: If authentication fails.
        """
        try:
            # Try to get tokens from database
            logger.info("Loading Spotify tokens from database...")
            tokens = self._get_tokens_from_db()

            # Create auth manager with guild-specific credentials
            # Use MemoryCacheHandler to avoid file-based caching issues in containers
            # Set open_browser=False to prevent interactive prompts in headless environment
            auth_manager = SpotifyOAuth(
                client_id=self.credentials['client_id'],
                client_secret=self.credentials['client_secret'],
                redirect_uri=self.credentials['redirect_uri'],
                scope="playlist-modify-public playlist-modify-private user-read-private",
                requests_timeout=10,
                open_browser=False,
                cache_handler=MemoryCacheHandler(),
            )

            # Set token info
            import time
            token_info = {
                'access_token': tokens['access_token'],
                'refresh_token': tokens['refresh_token'],
                'expires_at': tokens['expires_at'],
                'scope': 'playlist-modify-public playlist-modify-private user-read-private',
                'token_type': 'Bearer',
            }

            auth_manager.token_info = token_info

            # Check if token needs refresh
            if time.time() > tokens['expires_at'] - 60:  # Refresh if expiring within 1 minute
                logger.info("Access token expired, refreshing...")
                try:
                    token_info = auth_manager.refresh_access_token(tokens['refresh_token'])
                    logger.info("Successfully refreshed access token")

                    # Save new tokens
                    self._save_tokens_to_db(
                        token_info['access_token'],
                        token_info.get('refresh_token', tokens['refresh_token']),  # May not return new refresh token
                        token_info['expires_at']
                    )
                except Exception as refresh_error:
                    logger.error(f"Token refresh failed: {refresh_error}")
                    raise ValueError(
                        f"Failed to refresh Spotify token: {refresh_error}. "
                        "Your refresh token may have expired. "
                        "Run: python scripts/setup_spotify_auth.py"
                    )
            else:
                logger.info("Using cached access token")

            # Create Spotify client using access token directly
            # This avoids auth_manager trying to do interactive auth in headless environments
            sp = spotipy.Spotify(auth=token_info['access_token'], requests_timeout=10)
            logger.info("Spotify authentication successful")
            return sp

        except ValueError:
            # Re-raise ValueError as-is (already has good message)
            raise
        except Exception as e:
            logger.error(f"Spotify authentication failed: {e}")
            raise ValueError(
                f"Failed to authenticate with Spotify: {e}. "
                "Run: python scripts/setup_spotify_auth.py"
            )

    def _get_user_id(self) -> str:
        """Get the authenticated user's Spotify ID.

        Returns:
            Spotify user ID.
        """
        try:
            logger.info("Getting user ID via direct API call...")
            # Use direct HTTP request instead of spotipy to avoid timeout issues
            import requests
            tokens = self._get_tokens_from_db()
            response = requests.get(
                'https://api.spotify.com/v1/me',
                headers={'Authorization': f'Bearer {tokens["access_token"]}'},
                timeout=10
            )
            response.raise_for_status()
            user_info = response.json()
            user_id = user_info['id']
            logger.info(f"Successfully retrieved user ID: {user_id}")
            return user_id
        except Exception as e:
            logger.error(f"Failed to get Spotify user ID: {e}", exc_info=True)
            raise

    def _retry_api_call(self, func, *args, max_retries=3, **kwargs):
        """Retry Spotify API calls with exponential backoff.

        Args:
            func: The Spotify API function to call.
            *args: Positional arguments for the function.
            max_retries: Maximum number of retry attempts.
            **kwargs: Keyword arguments for the function.

        Returns:
            API call result.

        Raises:
            Exception: If all retries fail.
        """
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempting API call: {func.__name__} (attempt {attempt + 1}/{max_retries})")
                result = func(*args, **kwargs)
                logger.debug(f"API call successful: {func.__name__}")
                return result
            except spotipy.exceptions.SpotifyException as e:
                logger.error(f"Spotify API error: {e.http_status} - {e.msg}")
                if e.http_status == 429:  # Rate limited
                    retry_after = int(e.headers.get('Retry-After', 1))
                    logger.warning(f"Rate limited. Retrying after {retry_after}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_after)
                elif e.http_status >= 500:  # Server error
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Spotify server error. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Unrecoverable Spotify error: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error in API call: {type(e).__name__}: {e}")
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"API call failed. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(wait_time)

        raise Exception(f"Failed after {max_retries} attempts")

    def _direct_search(self, query: str, limit: int = 3) -> Dict[str, Any]:
        """Perform direct HTTP search request to Spotify API.

        Args:
            query: The search query string.
            limit: Maximum number of results.

        Returns:
            Search results dictionary from Spotify API.
        """
        import requests
        tokens = self._get_tokens_from_db()

        params = {
            'q': query,
            'type': 'track',
            'limit': limit
        }

        response = requests.get(
            'https://api.spotify.com/v1/search',
            headers={'Authorization': f'Bearer {tokens["access_token"]}'},
            params=params,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def search_song(self, song_title: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search Spotify for a song by title.

        Args:
            song_title: Title of the song to search for.
            limit: Maximum number of results to return.

        Returns:
            List of track dictionaries with relevant information.
        """
        logger.info(f"Starting Spotify search for: {song_title}")
        try:
            # Try exact search first
            logger.info(f"Attempting exact search for: {song_title}")
            results = self._direct_search(
                query=f'track:"{song_title}"',
                limit=limit
            )
            logger.info(f"Exact search completed for: {song_title}")

            tracks = []
            if results['tracks']['items']:
                tracks = self._extract_track_info(results['tracks']['items'])
                logger.info(f"Found {len(tracks)} exact matches for '{song_title}'")
                return tracks

            # Try without quotes if exact search fails
            logger.info(f"Trying search without quotes for: {song_title}")
            results = self._direct_search(
                query=f'track:{song_title}',
                limit=limit
            )

            if results['tracks']['items']:
                tracks = self._extract_track_info(results['tracks']['items'])
                logger.info(f"Found {len(tracks)} matches for '{song_title}'")
                return tracks

            # Try variations if configured
            song_lower = song_title.lower()
            for key, variations in self.SONG_VARIATIONS.items():
                if key in song_lower:
                    for variation in variations:
                        logger.info(f"Trying variation: {variation}")
                        results = self._direct_search(
                            query=f'track:"{variation}"',
                            limit=limit
                        )
                        if results['tracks']['items']:
                            tracks = self._extract_track_info(results['tracks']['items'])
                            logger.info(f"Found {len(tracks)} matches using variation '{variation}'")
                            return tracks

            logger.warning(f"No Spotify matches found for '{song_title}'")
            return []

        except Exception as e:
            logger.error(f"Error searching for song '{song_title}': {e}")
            return []

    def _extract_track_info(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """Extract relevant track information from Spotify search results.

        Args:
            items: List of track items from Spotify API.

        Returns:
            List of simplified track dictionaries.
        """
        tracks = []
        for item in items:
            track = {
                'id': item['id'],
                'name': item['name'],
                'artist': ', '.join([artist['name'] for artist in item['artists']]),
                'album': item['album']['name'],
                'url': item['external_urls']['spotify'],
                'uri': item['uri'],
            }
            tracks.append(track)
        return tracks

    def get_track_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get track information from a Spotify URL.

        Args:
            url: Spotify track URL.

        Returns:
            Track dictionary or None if invalid.
        """
        try:
            # Extract track ID from URL
            if '/track/' in url:
                track_id = url.split('/track/')[1].split('?')[0]
            else:
                logger.error(f"Invalid Spotify track URL: {url}")
                return None

            track = self._retry_api_call(self.sp.track, track_id)
            return self._extract_track_info([track])[0]

        except Exception as e:
            logger.error(f"Error getting track from URL '{url}': {e}")
            return None

    def create_playlist(self, name: str, description: str = "", public: bool = True) -> Dict[str, str]:
        """Create a new Spotify playlist.

        Args:
            name: Playlist name.
            description: Playlist description.
            public: Whether the playlist should be public.

        Returns:
            Dictionary with 'id' and 'url' of created playlist.

        Raises:
            Exception: If playlist creation fails.
        """
        try:
            playlist = self._retry_api_call(
                self.sp.user_playlist_create,
                user=self.user_id,
                name=name,
                public=public,
                description=description
            )

            result = {
                'id': playlist['id'],
                'url': playlist['external_urls']['spotify'],
            }

            logger.info(f"Created Spotify playlist: {name} ({result['url']})")
            return result

        except Exception as e:
            logger.error(f"Failed to create playlist '{name}': {e}")
            raise

    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]):
        """Add tracks to a Spotify playlist.

        Args:
            playlist_id: Spotify playlist ID.
            track_uris: List of Spotify track URIs.

        Raises:
            Exception: If adding tracks fails.
        """
        try:
            # Spotify allows adding up to 100 tracks at once
            batch_size = 100
            for i in range(0, len(track_uris), batch_size):
                batch = track_uris[i:i + batch_size]
                self._retry_api_call(
                    self.sp.playlist_add_items,
                    playlist_id=playlist_id,
                    items=batch
                )
                logger.info(f"Added {len(batch)} tracks to playlist (batch {i // batch_size + 1})")

            logger.info(f"Successfully added all {len(track_uris)} tracks to playlist {playlist_id}")

        except Exception as e:
            logger.error(f"Failed to add tracks to playlist {playlist_id}: {e}")
            raise

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """Get Spotify authorization URL for web-based OAuth flow.

        Args:
            state: Optional state parameter to pass through OAuth flow (for guild_id and user_id).

        Returns:
            Authorization URL to redirect user to.
        """
        auth_manager = SpotifyOAuth(
            client_id=self.credentials['client_id'],
            client_secret=self.credentials['client_secret'],
            redirect_uri=self.credentials['redirect_uri'],
            scope="playlist-modify-public playlist-modify-private user-read-private",
            requests_timeout=10,
            state=state,
        )
        return auth_manager.get_authorize_url()

    def authenticate_with_code(self, code: str, user_id: Optional[int] = None):
        """Complete OAuth flow by exchanging authorization code for tokens.

        Args:
            code: Authorization code from Spotify callback.
            user_id: Discord user ID who authorized (optional).

        Raises:
            Exception: If token exchange fails.
        """
        try:
            auth_manager = SpotifyOAuth(
                client_id=self.credentials['client_id'],
                client_secret=self.credentials['client_secret'],
                redirect_uri=self.credentials['redirect_uri'],
                scope="playlist-modify-public playlist-modify-private user-read-private",
                requests_timeout=10,
                open_browser=False,
                cache_handler=MemoryCacheHandler(),
            )

            # Exchange code for tokens
            token_info = auth_manager.get_access_token(code, as_dict=True, check_cache=False)

            # Save tokens to database with guild_id and user_id
            self._save_tokens_to_db(
                token_info['access_token'],
                token_info['refresh_token'],
                token_info['expires_at'],
                user_id=user_id
            )

            logger.info(f"Spotify tokens saved for guild {self.guild_id} by user {user_id}")

            # Re-initialize the client with new tokens
            self.sp = self._authenticate()
            self.user_id = self._get_user_id()

        except Exception as e:
            logger.error(f"Failed to exchange code for tokens: {e}", exc_info=True)
            raise

    def is_authenticated(self) -> bool:
        """Check if Spotify client is authenticated.

        Returns:
            True if authenticated and tokens are valid, False otherwise.
        """
        try:
            # Try to get tokens from database
            tokens = self._get_tokens_from_db()

            # Check if access token is still valid
            import time
            if time.time() < tokens['expires_at'] - 60:
                return True

            # Try to refresh if expired
            auth_manager = SpotifyOAuth(
                client_id=Config.SPOTIFY_CLIENT_ID,
                client_secret=Config.SPOTIFY_CLIENT_SECRET,
                redirect_uri=Config.SPOTIFY_REDIRECT_URI,
                scope="playlist-modify-public playlist-modify-private user-read-private",
                requests_timeout=10,
                open_browser=False,
                cache_handler=MemoryCacheHandler(),
            )

            token_info = auth_manager.refresh_access_token(tokens['refresh_token'])
            self._save_tokens_to_db(
                token_info['access_token'],
                token_info.get('refresh_token', tokens['refresh_token']),
                token_info['expires_at']
            )
            return True

        except Exception:
            return False
