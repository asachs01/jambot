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
            guild_id INTEGER NOT NULL,
            song_title TEXT NOT NULL,
            spotify_track_id TEXT NOT NULL,
            spotify_track_name TEXT NOT NULL,
            artist TEXT NOT NULL,
            album TEXT NOT NULL,
            spotify_url TEXT NOT NULL,
            first_used DATE NOT NULL,
            last_used DATE NOT NULL,
            UNIQUE(guild_id, song_title)
        );

        CREATE TABLE IF NOT EXISTS setlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
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

        CREATE TABLE IF NOT EXISTS bot_configuration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER UNIQUE NOT NULL,
            jam_leader_ids TEXT NOT NULL,
            approver_ids TEXT NOT NULL,
            channel_id INTEGER,
            playlist_name_template TEXT,
            updated_at TIMESTAMP NOT NULL,
            updated_by INTEGER NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_songs_guild_title ON songs(guild_id, song_title);
        CREATE INDEX IF NOT EXISTS idx_setlists_guild_date ON setlists(guild_id, date);
        CREATE INDEX IF NOT EXISTS idx_setlist_songs_setlist_id ON setlist_songs(setlist_id);
        CREATE INDEX IF NOT EXISTS idx_setlist_songs_song_id ON setlist_songs(song_id);
        CREATE INDEX IF NOT EXISTS idx_bot_configuration_guild_id ON bot_configuration(guild_id);
        """

        with self.get_connection() as conn:
            conn.executescript(schema)

            # Migrate existing databases - add guild_id columns if they don't exist
            cursor = conn.execute("PRAGMA table_info(songs)")
            songs_columns = [row[1] for row in cursor.fetchall()]

            cursor = conn.execute("PRAGMA table_info(setlists)")
            setlists_columns = [row[1] for row in cursor.fetchall()]

            cursor = conn.execute("PRAGMA table_info(bot_configuration)")
            config_columns = [row[1] for row in cursor.fetchall()]

            # Migration for songs table
            if 'guild_id' not in songs_columns:
                logger.info("Migrating songs table to add guild_id column...")
                # Create new table with guild_id
                conn.execute("""
                    CREATE TABLE songs_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL DEFAULT 0,
                        song_title TEXT NOT NULL,
                        spotify_track_id TEXT NOT NULL,
                        spotify_track_name TEXT NOT NULL,
                        artist TEXT NOT NULL,
                        album TEXT NOT NULL,
                        spotify_url TEXT NOT NULL,
                        first_used DATE NOT NULL,
                        last_used DATE NOT NULL,
                        UNIQUE(guild_id, song_title)
                    )
                """)
                # Copy data (all existing songs assigned to guild_id 0 for backwards compatibility)
                conn.execute("""
                    INSERT INTO songs_new
                    SELECT id, 0 as guild_id, song_title, spotify_track_id, spotify_track_name,
                           artist, album, spotify_url, first_used, last_used
                    FROM songs
                """)
                # Drop old table and rename
                conn.execute("DROP TABLE songs")
                conn.execute("ALTER TABLE songs_new RENAME TO songs")
                conn.execute("CREATE INDEX idx_songs_guild_title ON songs(guild_id, song_title)")
                logger.info("Migrated songs table successfully")

            # Migration for setlists table
            if 'guild_id' not in setlists_columns:
                logger.info("Migrating setlists table to add guild_id column...")
                conn.execute("""
                    CREATE TABLE setlists_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL DEFAULT 0,
                        date TEXT NOT NULL,
                        time TEXT NOT NULL,
                        playlist_name TEXT NOT NULL,
                        spotify_playlist_id TEXT,
                        spotify_playlist_url TEXT,
                        created_at TIMESTAMP NOT NULL
                    )
                """)
                conn.execute("""
                    INSERT INTO setlists_new
                    SELECT id, 0 as guild_id, date, time, playlist_name,
                           spotify_playlist_id, spotify_playlist_url, created_at
                    FROM setlists
                """)
                conn.execute("DROP TABLE setlists")
                conn.execute("ALTER TABLE setlists_new RENAME TO setlists")
                conn.execute("CREATE INDEX idx_setlists_guild_date ON setlists(guild_id, date)")
                logger.info("Migrated setlists table successfully")

            # Migrate bot_configuration table columns
            if 'channel_id' not in config_columns:
                conn.execute("ALTER TABLE bot_configuration ADD COLUMN channel_id INTEGER")
                logger.info("Added channel_id column to bot_configuration table")

            if 'playlist_name_template' not in config_columns:
                conn.execute("ALTER TABLE bot_configuration ADD COLUMN playlist_name_template TEXT")
                logger.info("Added playlist_name_template column to bot_configuration table")

            logger.info("Database schema initialized successfully")

    def get_song_by_title(self, guild_id: int, song_title: str) -> Optional[Dict[str, Any]]:
        """Look up a song by title within a specific guild.

        Args:
            guild_id: Discord guild (server) ID.
            song_title: The song title to search for.

        Returns:
            Dictionary with song data if found, None otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM songs WHERE guild_id = ? AND song_title = ?",
                (guild_id, song_title)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def add_or_update_song(
        self,
        guild_id: int,
        song_title: str,
        spotify_track_id: str,
        spotify_track_name: str,
        artist: str,
        album: str,
        spotify_url: str
    ) -> int:
        """Add a new song or update existing song's last_used date within a specific guild.

        Args:
            guild_id: Discord guild (server) ID.
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
            # Check if song exists for this guild
            existing = self.get_song_by_title(guild_id, song_title)

            if existing:
                # Update last_used date
                conn.execute(
                    "UPDATE songs SET last_used = ? WHERE id = ?",
                    (today, existing['id'])
                )
                logger.info(f"Updated last_used for song in guild {guild_id}: {song_title}")
                return existing['id']
            else:
                # Insert new song
                cursor = conn.execute(
                    """INSERT INTO songs
                       (guild_id, song_title, spotify_track_id, spotify_track_name, artist, album, spotify_url, first_used, last_used)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (guild_id, song_title, spotify_track_id, spotify_track_name, artist, album, spotify_url, today, today)
                )
                logger.info(f"Added new song to database for guild {guild_id}: {song_title}")
                return cursor.lastrowid

    def create_setlist(self, guild_id: int, date: str, time: str, playlist_name: str) -> int:
        """Create a new setlist record for a specific guild.

        Args:
            guild_id: Discord guild (server) ID.
            date: Setlist date.
            time: Setlist time.
            playlist_name: Name of the Spotify playlist.

        Returns:
            Setlist ID.
        """
        created_at = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO setlists (guild_id, date, time, playlist_name, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (guild_id, date, time, playlist_name, created_at)
            )
            setlist_id = cursor.lastrowid
            logger.info(f"Created setlist for guild {guild_id}: {playlist_name} (ID: {setlist_id})")
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

    def get_setlist_by_date(self, guild_id: int, date: str) -> Optional[Dict[str, Any]]:
        """Get a setlist by date within a specific guild.

        Args:
            guild_id: Discord guild (server) ID.
            date: Setlist date.

        Returns:
            Setlist dictionary if found, None otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM setlists WHERE guild_id = ? AND date = ?",
                (guild_id, date)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def save_bot_configuration(
        self,
        guild_id: int,
        jam_leader_ids: List[int],
        approver_ids: List[int],
        channel_id: Optional[int] = None,
        playlist_name_template: Optional[str] = None,
        updated_by: Optional[int] = None
    ):
        """Save bot configuration for a guild.

        Args:
            guild_id: Discord guild (server) ID.
            jam_leader_ids: List of user IDs who can post setlists.
            approver_ids: List of user IDs who can approve songs.
            channel_id: Optional channel ID where playlists should be posted.
            playlist_name_template: Optional template for playlist names (use {date} and {time} as placeholders).
            updated_by: User ID who made the update (optional).
        """
        # Convert lists to JSON strings for storage
        import json
        jam_leader_ids_json = json.dumps(jam_leader_ids)
        approver_ids_json = json.dumps(approver_ids)
        updated_at = datetime.now().isoformat()

        with self.get_connection() as conn:
            # Use INSERT OR REPLACE to handle both create and update
            conn.execute(
                """INSERT OR REPLACE INTO bot_configuration
                   (guild_id, jam_leader_ids, approver_ids, channel_id, playlist_name_template, updated_at, updated_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (guild_id, jam_leader_ids_json, approver_ids_json, channel_id, playlist_name_template, updated_at, updated_by or 0)
            )
            logger.info(
                f"Saved bot configuration for guild {guild_id}: "
                f"{len(jam_leader_ids)} jam leaders, {len(approver_ids)} approvers, "
                f"channel: {channel_id}, playlist template: {playlist_name_template}"
            )

    def get_bot_configuration(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get bot configuration for a guild.

        Args:
            guild_id: Discord guild (server) ID.

        Returns:
            Dictionary with configuration data if found, None otherwise.
            Configuration includes 'jam_leader_ids' and 'approver_ids' as lists.
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM bot_configuration WHERE guild_id = ?",
                (guild_id,)
            )
            row = cursor.fetchone()
            if row:
                import json
                config = dict(row)
                # Parse JSON strings back to lists
                config['jam_leader_ids'] = json.loads(config['jam_leader_ids'])
                config['approver_ids'] = json.loads(config['approver_ids'])
                return config
            return None

    def is_jam_leader(self, guild_id: int, user_id: int) -> bool:
        """Check if a user is a jam leader for a guild.

        Args:
            guild_id: Discord guild (server) ID.
            user_id: Discord user ID to check.

        Returns:
            True if user is a jam leader, False otherwise.
        """
        config = self.get_bot_configuration(guild_id)
        if config:
            is_leader = user_id in config['jam_leader_ids']
            logger.info(
                f"Jam leader check for guild {guild_id}, user {user_id}: {is_leader} "
                f"(configured leaders: {config['jam_leader_ids']})"
            )
            return is_leader
        else:
            logger.warning(
                f"No bot configuration found for guild {guild_id}. "
                f"User {user_id} will not be recognized as jam leader. "
                f"Please run /jambot-setup to configure the bot."
            )
            return False

    def is_approver(self, guild_id: int, user_id: int) -> bool:
        """Check if a user is an approver for a guild.

        Args:
            guild_id: Discord guild (server) ID.
            user_id: Discord user ID to check.

        Returns:
            True if user is an approver, False otherwise.
        """
        config = self.get_bot_configuration(guild_id)
        if config:
            return user_id in config['approver_ids']
        return False

    def get_approver_ids(self, guild_id: int) -> List[int]:
        """Get list of approver user IDs for a guild.

        Args:
            guild_id: Discord guild (server) ID.

        Returns:
            List of approver user IDs, or empty list if not configured.
        """
        config = self.get_bot_configuration(guild_id)
        if config:
            return config['approver_ids']
        return []
