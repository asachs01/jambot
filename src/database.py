"""Database management for Jambot using SQLite."""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from src.config import Config
from src.logger import logger


class Database:
    """SQLite database interface for song and setlist management."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Uses Config.DATABASE_PATH if not provided.
        """
        self.db_path = db_path or Config.DATABASE_PATH
        self._ensure_directory()
        self._initialize_schema()

    def _ensure_directory(self):
        """Ensure the database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections.

        Yields:
            sqlite3.Connection: Database connection with row factory enabled.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            conn.close()

    def _initialize_schema(self):
        """Create database tables if they don't exist."""
        schema = """
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_title TEXT UNIQUE NOT NULL,
            spotify_track_id TEXT NOT NULL,
            spotify_track_name TEXT NOT NULL,
            artist TEXT NOT NULL,
            album TEXT NOT NULL,
            spotify_url TEXT NOT NULL,
            first_used DATE NOT NULL,
            last_used DATE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS setlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            playlist_name TEXT NOT NULL,
            spotify_playlist_id TEXT,
            spotify_playlist_url TEXT,
            created_at TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS setlist_songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setlist_id INTEGER NOT NULL,
            song_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            FOREIGN KEY (setlist_id) REFERENCES setlists(id),
            FOREIGN KEY (song_id) REFERENCES songs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(song_title);
        CREATE INDEX IF NOT EXISTS idx_setlists_date ON setlists(date);
        CREATE INDEX IF NOT EXISTS idx_setlist_songs_setlist_id ON setlist_songs(setlist_id);
        CREATE INDEX IF NOT EXISTS idx_setlist_songs_song_id ON setlist_songs(song_id);
        """

        with self.get_connection() as conn:
            conn.executescript(schema)
            logger.info("Database schema initialized successfully")

    def get_song_by_title(self, song_title: str) -> Optional[Dict[str, Any]]:
        """Look up a song by title.

        Args:
            song_title: The song title to search for.

        Returns:
            Dictionary with song data if found, None otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM songs WHERE song_title = ?",
                (song_title,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def add_or_update_song(
        self,
        song_title: str,
        spotify_track_id: str,
        spotify_track_name: str,
        artist: str,
        album: str,
        spotify_url: str
    ) -> int:
        """Add a new song or update existing song's last_used date.

        Args:
            song_title: Title of the song.
            spotify_track_id: Spotify track ID.
            spotify_track_name: Full track name from Spotify.
            artist: Artist name.
            album: Album name.
            spotify_url: Spotify URL for the track.

        Returns:
            Song ID (existing or newly created).
        """
        today = datetime.now().date().isoformat()

        with self.get_connection() as conn:
            # Check if song exists
            existing = self.get_song_by_title(song_title)

            if existing:
                # Update last_used date
                conn.execute(
                    "UPDATE songs SET last_used = ? WHERE id = ?",
                    (today, existing['id'])
                )
                logger.info(f"Updated last_used for song: {song_title}")
                return existing['id']
            else:
                # Insert new song
                cursor = conn.execute(
                    """INSERT INTO songs
                       (song_title, spotify_track_id, spotify_track_name, artist, album, spotify_url, first_used, last_used)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (song_title, spotify_track_id, spotify_track_name, artist, album, spotify_url, today, today)
                )
                logger.info(f"Added new song to database: {song_title}")
                return cursor.lastrowid

    def create_setlist(self, date: str, time: str, playlist_name: str) -> int:
        """Create a new setlist record.

        Args:
            date: Setlist date.
            time: Setlist time.
            playlist_name: Name of the Spotify playlist.

        Returns:
            Setlist ID.
        """
        created_at = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO setlists (date, time, playlist_name, created_at)
                   VALUES (?, ?, ?, ?)""",
                (date, time, playlist_name, created_at)
            )
            setlist_id = cursor.lastrowid
            logger.info(f"Created setlist: {playlist_name} (ID: {setlist_id})")
            return setlist_id

    def update_setlist_playlist(self, setlist_id: int, playlist_id: str, playlist_url: str):
        """Update setlist with Spotify playlist information.

        Args:
            setlist_id: Setlist database ID.
            playlist_id: Spotify playlist ID.
            playlist_url: Spotify playlist URL.
        """
        with self.get_connection() as conn:
            conn.execute(
                """UPDATE setlists
                   SET spotify_playlist_id = ?, spotify_playlist_url = ?
                   WHERE id = ?""",
                (playlist_id, playlist_url, setlist_id)
            )
            logger.info(f"Updated setlist {setlist_id} with Spotify playlist: {playlist_url}")

    def add_setlist_song(self, setlist_id: int, song_id: int, position: int):
        """Add a song to a setlist at a specific position.

        Args:
            setlist_id: Setlist database ID.
            song_id: Song database ID.
            position: Position in setlist (1-indexed).
        """
        with self.get_connection() as conn:
            conn.execute(
                """INSERT INTO setlist_songs (setlist_id, song_id, position)
                   VALUES (?, ?, ?)""",
                (setlist_id, song_id, position)
            )
            logger.debug(f"Added song {song_id} to setlist {setlist_id} at position {position}")

    def get_setlist_songs(self, setlist_id: int) -> List[Dict[str, Any]]:
        """Get all songs in a setlist, ordered by position.

        Args:
            setlist_id: Setlist database ID.

        Returns:
            List of song dictionaries with position information.
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT s.*, ss.position
                   FROM songs s
                   JOIN setlist_songs ss ON s.id = ss.song_id
                   WHERE ss.setlist_id = ?
                   ORDER BY ss.position""",
                (setlist_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_setlist_by_date(self, date: str) -> Optional[Dict[str, Any]]:
        """Get a setlist by date.

        Args:
            date: Setlist date.

        Returns:
            Setlist dictionary if found, None otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM setlists WHERE date = ?",
                (date,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
