"""Spotify API integration for Jambot."""
import time
from typing import List, Optional, Dict, Any
import spotipy
from spotipy.oauth2 import SpotifyOAuth
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

    def __init__(self):
        """Initialize Spotify client with OAuth."""
        self.sp = self._authenticate()
        self.user_id = self._get_user_id()
        logger.info(f"Spotify client initialized for user: {self.user_id}")

    def _authenticate(self) -> spotipy.Spotify:
        """Authenticate with Spotify using refresh token.

        Returns:
            Authenticated Spotify client.

        Raises:
            ValueError: If authentication fails.
        """
        try:
            auth_manager = SpotifyOAuth(
                client_id=Config.SPOTIFY_CLIENT_ID,
                client_secret=Config.SPOTIFY_CLIENT_SECRET,
                redirect_uri=Config.SPOTIFY_REDIRECT_URI,
                scope="playlist-modify-public playlist-modify-private",
            )

            # Set the refresh token
            token_info = {
                'refresh_token': Config.SPOTIFY_REFRESH_TOKEN,
                'access_token': None,
                'expires_at': 0,
            }
            auth_manager.token_info = token_info

            # Force token refresh
            token_info = auth_manager.get_access_token(as_dict=True)

            sp = spotipy.Spotify(auth_manager=auth_manager)
            logger.info("Spotify authentication successful")
            return sp

        except Exception as e:
            logger.error(f"Spotify authentication failed: {e}")
            raise ValueError(f"Failed to authenticate with Spotify: {e}")

    def _get_user_id(self) -> str:
        """Get the authenticated user's Spotify ID.

        Returns:
            Spotify user ID.
        """
        try:
            user_info = self.sp.current_user()
            return user_info['id']
        except Exception as e:
            logger.error(f"Failed to get Spotify user ID: {e}")
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
                return func(*args, **kwargs)
            except spotipy.exceptions.SpotifyException as e:
                if e.http_status == 429:  # Rate limited
                    retry_after = int(e.headers.get('Retry-After', 1))
                    logger.warning(f"Rate limited. Retrying after {retry_after}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_after)
                elif e.http_status >= 500:  # Server error
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Spotify server error. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    raise
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"API call failed. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(wait_time)

        raise Exception(f"Failed after {max_retries} attempts")

    def search_song(self, song_title: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search Spotify for a song by title.

        Args:
            song_title: Title of the song to search for.
            limit: Maximum number of results to return.

        Returns:
            List of track dictionaries with relevant information.
        """
        try:
            # Try exact search first
            results = self._retry_api_call(
                self.sp.search,
                q=f'track:"{song_title}" genre:bluegrass',
                type='track',
                limit=limit
            )

            tracks = []
            if results['tracks']['items']:
                tracks = self._extract_track_info(results['tracks']['items'])
                logger.info(f"Found {len(tracks)} exact matches for '{song_title}'")
                return tracks

            # Try without quotes if exact search fails
            results = self._retry_api_call(
                self.sp.search,
                q=f'track:{song_title} genre:bluegrass',
                type='track',
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
                        results = self._retry_api_call(
                            self.sp.search,
                            q=f'track:"{variation}" genre:bluegrass',
                            type='track',
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
