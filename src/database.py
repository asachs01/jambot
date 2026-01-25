"""Database management for Jambot using PostgreSQL."""
import psycopg2
import psycopg2.extras
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from src.config import Config
from src.logger import logger


class Database:
    """PostgreSQL database interface for song and setlist management."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection.

        Args:
            database_url: PostgreSQL connection URL. Uses Config.DATABASE_URL if not provided.
        """
        self.database_url = database_url or Config.DATABASE_URL

        if not self.database_url:
            raise ValueError(
                "DATABASE_URL environment variable is required. "
                "Format: postgresql://user:password@host:port/database?sslmode=require"
            )

        self._initialize_schema()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections.

        Yields:
            psycopg2.connection: Database connection with dict cursor.
        """
        conn = psycopg2.connect(self.database_url)
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
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
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
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            playlist_name TEXT NOT NULL,
            spotify_playlist_id TEXT,
            spotify_playlist_url TEXT,
            created_at TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS setlist_songs (
            id SERIAL PRIMARY KEY,
            setlist_id INTEGER NOT NULL REFERENCES setlists(id),
            song_id INTEGER NOT NULL REFERENCES songs(id),
            position INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bot_configuration (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT UNIQUE NOT NULL,
            jam_leader_ids TEXT NOT NULL,
            approver_ids TEXT NOT NULL,
            channel_id BIGINT,
            playlist_name_template TEXT,
            spotify_client_id TEXT,
            spotify_client_secret TEXT,
            spotify_redirect_uri TEXT,
            setlist_intro_pattern TEXT,
            setlist_song_pattern TEXT,
            updated_at TIMESTAMP NOT NULL,
            updated_by BIGINT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS spotify_tokens (
            guild_id BIGINT PRIMARY KEY,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at BIGINT NOT NULL,
            authorized_by BIGINT NOT NULL,
            created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW()),
            updated_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())
        );

        CREATE TABLE IF NOT EXISTS active_workflows (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            summary_message_id BIGINT UNIQUE NOT NULL,
            original_channel_id BIGINT,
            original_message_id BIGINT,
            song_matches JSONB NOT NULL,
            selections JSONB DEFAULT '{}',
            message_ids JSONB DEFAULT '[]',
            approver_ids JSONB DEFAULT '[]',
            setlist_data JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_songs_guild_title ON songs(guild_id, song_title);
        CREATE INDEX IF NOT EXISTS idx_setlists_guild_date ON setlists(guild_id, date);
        CREATE INDEX IF NOT EXISTS idx_setlist_songs_setlist_id ON setlist_songs(setlist_id);
        CREATE INDEX IF NOT EXISTS idx_setlist_songs_song_id ON setlist_songs(song_id);
        CREATE INDEX IF NOT EXISTS idx_bot_configuration_guild_id ON bot_configuration(guild_id);
        CREATE INDEX IF NOT EXISTS idx_spotify_tokens_guild_id ON spotify_tokens(guild_id);
        CREATE INDEX IF NOT EXISTS idx_active_workflows_summary_message ON active_workflows(summary_message_id);

        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            feedback_type TEXT NOT NULL,
            message TEXT NOT NULL,
            context TEXT,
            rating INTEGER,
            created_at TIMESTAMP DEFAULT NOW(),
            notified_maintainer BOOLEAN DEFAULT FALSE
        );

        CREATE TABLE IF NOT EXISTS usage_stats (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            event_type TEXT NOT NULL,
            event_data JSONB,
            event_date DATE DEFAULT CURRENT_DATE,
            count INTEGER DEFAULT 1,
            UNIQUE(guild_id, event_type, event_date, event_data)
        );

        CREATE INDEX IF NOT EXISTS idx_feedback_guild_id ON feedback(guild_id);
        CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at);
        CREATE INDEX IF NOT EXISTS idx_usage_stats_guild_event ON usage_stats(guild_id, event_type, event_date);

        CREATE TABLE IF NOT EXISTS chord_charts (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            title TEXT NOT NULL,
            chart_title TEXT,
            lyrics JSONB,
            keys JSONB NOT NULL,
            created_by BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            alternate_titles JSONB,
            source TEXT DEFAULT 'user_created',
            status TEXT DEFAULT 'approved',
            UNIQUE(guild_id, title)
        );

        CREATE INDEX IF NOT EXISTS idx_chord_charts_guild_title ON chord_charts(guild_id, title);

        CREATE TABLE IF NOT EXISTS generation_history (
            id SERIAL PRIMARY KEY,
            chart_id INTEGER REFERENCES chord_charts(id),
            prompt TEXT NOT NULL,
            response JSONB NOT NULL,
            model TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_generation_history_chart_id ON generation_history(chart_id);
        """

        # Migration for existing databases: add setlist pattern columns if they don't exist
        migration = """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'bot_configuration' AND column_name = 'setlist_intro_pattern') THEN
                ALTER TABLE bot_configuration ADD COLUMN setlist_intro_pattern TEXT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'bot_configuration' AND column_name = 'setlist_song_pattern') THEN
                ALTER TABLE bot_configuration ADD COLUMN setlist_song_pattern TEXT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'active_workflows' AND column_name = 'setlist_data') THEN
                ALTER TABLE active_workflows ADD COLUMN setlist_data JSONB;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'active_workflows' AND column_name = 'status') THEN
                ALTER TABLE active_workflows ADD COLUMN status VARCHAR(20) DEFAULT 'pending';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'active_workflows' AND column_name = 'expires_at') THEN
                ALTER TABLE active_workflows ADD COLUMN expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '48 hours');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'active_workflows' AND column_name = 'initiated_by') THEN
                ALTER TABLE active_workflows ADD COLUMN initiated_by BIGINT;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'chord_charts' AND column_name = 'alternate_titles') THEN
                ALTER TABLE chord_charts ADD COLUMN alternate_titles JSONB;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'chord_charts' AND column_name = 'source') THEN
                ALTER TABLE chord_charts ADD COLUMN source TEXT DEFAULT 'user_created';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'chord_charts' AND column_name = 'status') THEN
                ALTER TABLE chord_charts ADD COLUMN status TEXT DEFAULT 'approved';
            END IF;
            -- Enable pg_trgm extension for fuzzy text search
            CREATE EXTENSION IF NOT EXISTS pg_trgm;
        END $$;
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(schema)
            cursor.execute(migration)
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
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT * FROM songs WHERE guild_id = %s AND song_title = %s",
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
            cursor = conn.cursor()

            # Use upsert (INSERT ... ON CONFLICT)
            cursor.execute(
                """INSERT INTO songs
                   (guild_id, song_title, spotify_track_id, spotify_track_name, artist, album, spotify_url, first_used, last_used)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (guild_id, song_title) DO UPDATE SET
                       last_used = EXCLUDED.last_used,
                       spotify_track_id = EXCLUDED.spotify_track_id,
                       spotify_track_name = EXCLUDED.spotify_track_name,
                       artist = EXCLUDED.artist,
                       album = EXCLUDED.album,
                       spotify_url = EXCLUDED.spotify_url
                   RETURNING id""",
                (guild_id, song_title, spotify_track_id, spotify_track_name, artist, album, spotify_url, today, today)
            )
            song_id = cursor.fetchone()[0]
            logger.info(f"Added/updated song in database for guild {guild_id}: {song_title}")
            return song_id

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
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO setlists (guild_id, date, time, playlist_name, created_at)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING id""",
                (guild_id, date, time, playlist_name, created_at)
            )
            setlist_id = cursor.fetchone()[0]
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
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE setlists
                   SET spotify_playlist_id = %s, spotify_playlist_url = %s
                   WHERE id = %s""",
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
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO setlist_songs (setlist_id, song_id, position)
                   VALUES (%s, %s, %s)""",
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
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                """SELECT s.*, ss.position
                   FROM songs s
                   JOIN setlist_songs ss ON s.id = ss.song_id
                   WHERE ss.setlist_id = %s
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
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT * FROM setlists WHERE guild_id = %s AND date = %s",
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
        spotify_client_id: Optional[str] = None,
        spotify_client_secret: Optional[str] = None,
        spotify_redirect_uri: Optional[str] = None,
        setlist_intro_pattern: Optional[str] = None,
        setlist_song_pattern: Optional[str] = None,
        updated_by: Optional[int] = None
    ):
        """Save bot configuration for a guild.

        Args:
            guild_id: Discord guild (server) ID.
            jam_leader_ids: List of user IDs who can post setlists.
            approver_ids: List of user IDs who can approve songs.
            channel_id: Optional channel ID where playlists should be posted.
            playlist_name_template: Optional template for playlist names (use {date} and {time} as placeholders).
            spotify_client_id: Optional Spotify app client ID for this guild.
            spotify_client_secret: Optional Spotify app client secret for this guild.
            spotify_redirect_uri: Optional Spotify redirect URI for this guild.
            setlist_intro_pattern: Optional regex pattern for setlist intro line.
            setlist_song_pattern: Optional regex pattern for song lines.
            updated_by: User ID who made the update (optional).
        """
        # Convert lists to JSON strings for storage
        import json
        jam_leader_ids_json = json.dumps(jam_leader_ids)
        approver_ids_json = json.dumps(approver_ids)
        updated_at = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Use upsert (INSERT ... ON CONFLICT)
            cursor.execute(
                """INSERT INTO bot_configuration
                   (guild_id, jam_leader_ids, approver_ids, channel_id, playlist_name_template,
                    spotify_client_id, spotify_client_secret, spotify_redirect_uri,
                    setlist_intro_pattern, setlist_song_pattern, updated_at, updated_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (guild_id) DO UPDATE SET
                       jam_leader_ids = EXCLUDED.jam_leader_ids,
                       approver_ids = EXCLUDED.approver_ids,
                       channel_id = EXCLUDED.channel_id,
                       playlist_name_template = EXCLUDED.playlist_name_template,
                       spotify_client_id = EXCLUDED.spotify_client_id,
                       spotify_client_secret = EXCLUDED.spotify_client_secret,
                       spotify_redirect_uri = EXCLUDED.spotify_redirect_uri,
                       setlist_intro_pattern = EXCLUDED.setlist_intro_pattern,
                       setlist_song_pattern = EXCLUDED.setlist_song_pattern,
                       updated_at = EXCLUDED.updated_at,
                       updated_by = EXCLUDED.updated_by""",
                (guild_id, jam_leader_ids_json, approver_ids_json, channel_id, playlist_name_template,
                 spotify_client_id, spotify_client_secret, spotify_redirect_uri,
                 setlist_intro_pattern, setlist_song_pattern, updated_at, updated_by or 0)
            )
            logger.info(
                f"Saved bot configuration for guild {guild_id}: "
                f"{len(jam_leader_ids)} jam leaders, {len(approver_ids)} approvers, "
                f"channel: {channel_id}, playlist template: {playlist_name_template}, "
                f"spotify credentials: {'configured' if spotify_client_id else 'not configured'}"
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
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT * FROM bot_configuration WHERE guild_id = %s",
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

    def update_setlist_patterns(
        self,
        guild_id: int,
        setlist_intro_pattern: Optional[str] = None,
        setlist_song_pattern: Optional[str] = None,
        updated_by: Optional[int] = None
    ) -> bool:
        """Update only the setlist pattern configuration for a guild.

        Args:
            guild_id: Discord guild (server) ID.
            setlist_intro_pattern: Regex pattern for setlist intro line (None to keep existing).
            setlist_song_pattern: Regex pattern for song lines (None to keep existing).
            updated_by: User ID who made the update (optional).

        Returns:
            True if update was successful, False if no configuration exists for guild.
        """
        # Check if configuration exists
        config = self.get_bot_configuration(guild_id)
        if not config:
            logger.warning(f"Cannot update setlist patterns: no configuration found for guild {guild_id}")
            return False

        updated_at = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Build dynamic update based on what's provided
            updates = []
            params = []

            if setlist_intro_pattern is not None:
                updates.append("setlist_intro_pattern = %s")
                params.append(setlist_intro_pattern)
            if setlist_song_pattern is not None:
                updates.append("setlist_song_pattern = %s")
                params.append(setlist_song_pattern)

            updates.append("updated_at = %s")
            params.append(updated_at)
            if updated_by:
                updates.append("updated_by = %s")
                params.append(updated_by)

            params.append(guild_id)

            cursor.execute(
                f"UPDATE bot_configuration SET {', '.join(updates)} WHERE guild_id = %s",
                params
            )
            logger.info(f"Updated setlist patterns for guild {guild_id}")
            return True

    def get_setlist_patterns(self, guild_id: int) -> Dict[str, Optional[str]]:
        """Get the setlist patterns for a guild.

        Args:
            guild_id: Discord guild (server) ID.

        Returns:
            Dictionary with 'intro_pattern' and 'song_pattern' keys (values may be None).
        """
        config = self.get_bot_configuration(guild_id)
        if config:
            return {
                'intro_pattern': config.get('setlist_intro_pattern'),
                'song_pattern': config.get('setlist_song_pattern')
            }
        return {'intro_pattern': None, 'song_pattern': None}

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

    def is_spotify_authorized(self, guild_id: int) -> bool:
        """Check if Spotify tokens exist for a guild.

        Args:
            guild_id: Discord guild (server) ID.

        Returns:
            True if Spotify tokens exist, False otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM spotify_tokens WHERE guild_id = %s",
                (guild_id,)
            )
            return cursor.fetchone() is not None

    # --- Chord Chart Methods ---

    def create_chord_chart(
        self,
        guild_id: int,
        title: str,
        keys: List[Dict[str, Any]],
        created_by: int,
        chart_title: Optional[str] = None,
        lyrics: Optional[List[Dict[str, Any]]] = None,
        source: str = 'user_created',
        status: str = 'approved',
        alternate_titles: Optional[List[str]] = None,
    ) -> int:
        """Create or update a chord chart.

        Args:
            guild_id: Discord guild (server) ID.
            title: Song title.
            keys: List of key entry dicts.
            created_by: Discord user ID.
            chart_title: Optional abbreviated title.
            lyrics: Optional lyrics data.
            source: Source of chart ('user_created' or 'ai_generated').
            status: Chart status ('draft', 'approved', 'rejected').
            alternate_titles: Optional list of alternate title spellings.

        Returns:
            Chart database ID.
        """
        import json

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO chord_charts
                   (guild_id, title, chart_title, lyrics, keys, created_by, source, status, alternate_titles)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (guild_id, title) DO UPDATE SET
                       chart_title = EXCLUDED.chart_title,
                       lyrics = EXCLUDED.lyrics,
                       keys = EXCLUDED.keys,
                       source = EXCLUDED.source,
                       status = EXCLUDED.status,
                       alternate_titles = EXCLUDED.alternate_titles,
                       updated_at = NOW()
                   RETURNING id""",
                (
                    guild_id, title, chart_title,
                    json.dumps(lyrics) if lyrics else None,
                    json.dumps(keys),
                    created_by,
                    source,
                    status,
                    json.dumps(alternate_titles) if alternate_titles else None,
                )
            )
            chart_id = cursor.fetchone()[0]
            logger.info(f"Created/updated chord chart '{title}' for guild {guild_id} (source={source}, status={status})")
            return chart_id

    def get_chord_chart(self, guild_id: int, title: str) -> Optional[Dict[str, Any]]:
        """Get a chord chart by exact title.

        Args:
            guild_id: Discord guild (server) ID.
            title: Exact song title.

        Returns:
            Chart dict if found, None otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT * FROM chord_charts WHERE guild_id = %s AND title = %s",
                (guild_id, title)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def fuzzy_search_chord_chart(self, guild_id: int, query: str) -> Optional[Dict[str, Any]]:
        """Search for a chord chart using fuzzy text matching with pg_trgm.

        Args:
            guild_id: Discord guild (server) ID.
            query: Search string (song title).

        Returns:
            Best matching chart dict if found, None otherwise.
        """
        import json
        query_lower = query.lower()

        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            # Try fuzzy match using pg_trgm similarity or alternate_titles array containment
            cursor.execute(
                """SELECT *
                   FROM chord_charts
                   WHERE guild_id = %s AND (
                       LOWER(title) %% %s
                       OR alternate_titles @> %s::jsonb
                   )
                   ORDER BY similarity(LOWER(title), %s) DESC
                   LIMIT 1""",
                (guild_id, query_lower, json.dumps([query_lower]), query_lower)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def create_generation_history(
        self,
        chart_id: int,
        prompt: str,
        response: Dict[str, Any],
        model: str
    ) -> int:
        """Create a generation history record for an AI-generated chart.

        Args:
            chart_id: Chart database ID.
            prompt: LLM prompt used for generation.
            response: Raw LLM response data.
            model: Model identifier (e.g., 'gpt-4', 'claude-3-sonnet-20240229').

        Returns:
            Generation history ID.
        """
        import json

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO generation_history
                   (chart_id, prompt, response, model)
                   VALUES (%s, %s, %s, %s)
                   RETURNING id""",
                (chart_id, prompt, json.dumps(response), model)
            )
            history_id = cursor.fetchone()[0]
            logger.info(f"Created generation history {history_id} for chart {chart_id} using {model}")
            return history_id

    def search_chord_charts(self, guild_id: int, query: str) -> List[Dict[str, Any]]:
        """Search chord charts by title (case-insensitive, substring match).

        Args:
            guild_id: Discord guild (server) ID.
            query: Search string.

        Returns:
            List of matching chart dicts.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT * FROM chord_charts WHERE guild_id = %s AND title ILIKE %s ORDER BY title",
                (guild_id, f"%{query}%")
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_chord_charts(self, guild_id: int) -> List[Dict[str, Any]]:
        """List all chord charts for a guild.

        Args:
            guild_id: Discord guild (server) ID.

        Returns:
            List of chart dicts.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT * FROM chord_charts WHERE guild_id = %s ORDER BY title",
                (guild_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_chord_charts_filtered(
        self,
        guild_id: int,
        status: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> tuple:
        """List chord charts with optional status filter and pagination.

        Args:
            guild_id: Discord guild (server) ID.
            status: Filter by status ('pending'|'approved'|'rejected'|None for all).
            limit: Results per page (default 10).
            offset: Skip N results (for pagination).

        Returns:
            Tuple of (chart_list, total_count).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Build WHERE clause
            where_clause = "WHERE guild_id = %s"
            params = [guild_id]

            if status and status != 'all':
                where_clause += " AND status = %s"
                params.append(status)

            # Get total count
            cursor.execute(f"SELECT COUNT(*) as count FROM chord_charts {where_clause}", params)
            total = cursor.fetchone()['count']

            # Get paginated results
            query = f"""
                SELECT id, title, chart_title, status, created_by, created_at
                FROM chord_charts {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])
            cursor.execute(query, params)

            return [dict(row) for row in cursor.fetchall()], total

    def update_chord_chart_keys(
        self, guild_id: int, title: str, keys: List[Dict[str, Any]]
    ):
        """Update the keys array for a chord chart (e.g. after transposition).

        Args:
            guild_id: Discord guild (server) ID.
            title: Song title.
            keys: Updated keys list.
        """
        import json

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE chord_charts SET keys = %s, updated_at = NOW() WHERE guild_id = %s AND title = %s",
                (json.dumps(keys), guild_id, title)
            )
            logger.info(f"Updated keys for chart '{title}' in guild {guild_id}")

    def update_chord_chart_status(
        self,
        guild_id: int,
        title: str,
        status: str,
        approved_by: Optional[int] = None
    ):
        """Update the status of a chord chart.

        Args:
            guild_id: Discord guild (server) ID.
            title: Song title.
            status: New status ('draft', 'approved', 'archived').
            approved_by: User ID who approved (if status is 'approved').
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status == 'approved' and approved_by is not None:
                cursor.execute(
                    """UPDATE chord_charts
                       SET status = %s, approved_by = %s, approved_at = NOW(), updated_at = NOW()
                       WHERE guild_id = %s AND title = %s""",
                    (status, approved_by, guild_id, title)
                )
            else:
                cursor.execute(
                    """UPDATE chord_charts
                       SET status = %s, updated_at = NOW()
                       WHERE guild_id = %s AND title = %s""",
                    (status, guild_id, title)
                )
            logger.info(f"Updated status to '{status}' for chart '{title}' in guild {guild_id}")

    def get_draft_charts(self, guild_id: int) -> List[Dict[str, Any]]:
        """List all draft chord charts for a guild.

        Args:
            guild_id: Discord guild (server) ID.

        Returns:
            List of draft chart dicts.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT * FROM chord_charts WHERE guild_id = %s AND status = 'draft' ORDER BY title",
                (guild_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_approved_charts(self, guild_id: int) -> List[Dict[str, Any]]:
        """List all approved chord charts for a guild.

        Args:
            guild_id: Discord guild (server) ID.

        Returns:
            List of approved chart dicts.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT * FROM chord_charts WHERE guild_id = %s AND status = 'approved' ORDER BY title",
                (guild_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def save_workflow(self, workflow_data: Dict, summary_message_id: int) -> None:
        """Save or update workflow to database.

        Args:
            workflow_data: Complete workflow dict from bot.active_workflows
            summary_message_id: Discord message ID used as unique key
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO active_workflows (
                    guild_id, summary_message_id, original_channel_id,
                    original_message_id, song_matches, selections,
                    message_ids, approver_ids, setlist_data, initiated_by, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (summary_message_id)
                DO UPDATE SET
                    selections = EXCLUDED.selections,
                    setlist_data = EXCLUDED.setlist_data,
                    updated_at = NOW()
            """, (
                workflow_data['guild_id'],
                summary_message_id,
                workflow_data.get('original_channel_id'),
                workflow_data.get('setlist_data', {}).get('original_message_id'),
                json.dumps(workflow_data['song_matches']),
                json.dumps(workflow_data['selections']),
                json.dumps(workflow_data['message_ids']),
                json.dumps(workflow_data.get('approver_ids', [])),
                json.dumps(workflow_data.get('setlist_data', {})),
                workflow_data.get('initiated_by')
            ))

    def get_workflow(self, summary_message_id: int) -> Optional[Dict]:
        """Retrieve workflow by summary message ID.

        Args:
            summary_message_id: Discord message ID

        Returns:
            Workflow data dict or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT guild_id, summary_message_id, original_channel_id,
                       original_message_id, song_matches, selections,
                       message_ids, approver_ids, setlist_data
                FROM active_workflows
                WHERE summary_message_id = %s
            """, (summary_message_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return {
                'guild_id': row[0],
                'summary_message_id': row[1],
                'original_channel_id': row[2],
                'original_message_id': row[3],
                'song_matches': row[4],  # Already parsed from JSONB
                'selections': row[5],
                'message_ids': row[6],
                'approver_ids': row[7],
                'setlist_data': row[8]
            }

    def get_all_active_workflows(self) -> List[Dict]:
        """Retrieve all active workflows for startup restoration.

        Returns:
            List of workflow data dicts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT guild_id, summary_message_id, original_channel_id,
                       original_message_id, song_matches, selections,
                       message_ids, approver_ids, setlist_data
                FROM active_workflows
                ORDER BY created_at ASC
            """)

            workflows = []
            for row in cursor.fetchall():
                workflows.append({
                    'guild_id': row[0],
                    'summary_message_id': row[1],
                    'original_channel_id': row[2],
                    'original_message_id': row[3],
                    'song_matches': row[4],
                    'selections': row[5],
                    'message_ids': row[6],
                    'approver_ids': row[7],
                    'setlist_data': row[8]
                })
            return workflows

    def update_workflow_selection(self, summary_message_id: int, song_number: int, track: Dict) -> None:
        """Update single song selection in workflow.

        Args:
            summary_message_id: Workflow identifier
            song_number: Song number (1-based)
            track: Spotify track info dict
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Use jsonb_set to update nested key without full read-modify-write
            cursor.execute("""
                UPDATE active_workflows
                SET selections = jsonb_set(
                        selections,
                        %s,
                        %s,
                        true
                    ),
                    updated_at = NOW()
                WHERE summary_message_id = %s
            """, (
                [str(song_number)],  # JSONB path array
                json.dumps(track),
                summary_message_id
            ))

    def delete_workflow(self, summary_message_id: int) -> None:
        """Delete workflow from database.

        Args:
            summary_message_id: Workflow identifier
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM active_workflows
                WHERE summary_message_id = %s
            """, (summary_message_id,))

    def save_feedback(
        self,
        guild_id: int,
        user_id: int,
        feedback_type: str,
        message: str,
        context: Optional[str] = None,
        rating: Optional[int] = None
    ) -> int:
        """Save user feedback to database.

        Args:
            guild_id: Discord guild (server) ID.
            user_id: Discord user ID who submitted feedback.
            feedback_type: Type of feedback (bug, feature, general).
            message: Feedback message content.
            context: Optional additional context.
            rating: Optional satisfaction rating (1-5).

        Returns:
            Feedback ID.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO feedback
                   (guild_id, user_id, feedback_type, message, context, rating)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (guild_id, user_id, feedback_type, message, context, rating)
            )
            feedback_id = cursor.fetchone()[0]
            logger.info(f"Saved feedback {feedback_id} from user {user_id} in guild {guild_id}")
            return feedback_id

    def mark_feedback_notified(self, feedback_id: int) -> None:
        """Mark feedback as having notified maintainer.

        Args:
            feedback_id: Feedback database ID.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE feedback SET notified_maintainer = TRUE WHERE id = %s",
                (feedback_id,)
            )

    def get_unnotified_feedback(self) -> List[Dict[str, Any]]:
        """Get all feedback that hasn't notified maintainer yet.

        Returns:
            List of feedback dictionaries.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                """SELECT * FROM feedback
                   WHERE notified_maintainer = FALSE
                   ORDER BY created_at ASC"""
            )
            return [dict(row) for row in cursor.fetchall()]

    def track_usage_event(
        self,
        guild_id: int,
        event_type: str,
        event_data: Optional[Dict] = None
    ) -> None:
        """Track a usage event with upsert (increment count if exists).

        Args:
            guild_id: Discord guild (server) ID.
            event_type: Type of event (e.g., 'playlist_created', 'command_used').
            event_data: Optional additional data as JSON.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Use upsert to increment count for existing events
            cursor.execute(
                """INSERT INTO usage_stats (guild_id, event_type, event_data, count)
                   VALUES (%s, %s, %s, 1)
                   ON CONFLICT (guild_id, event_type, event_date, event_data)
                   DO UPDATE SET count = usage_stats.count + 1""",
                (guild_id, event_type, json.dumps(event_data) if event_data else None)
            )

    def save_satisfaction_rating(
        self,
        guild_id: int,
        playlist_id: str,
        rating: int
    ) -> None:
        """Save playlist satisfaction rating.

        Args:
            guild_id: Discord guild (server) ID.
            playlist_id: Spotify playlist ID.
            rating: 1 for thumbs up, -1 for thumbs down.
        """
        self.track_usage_event(
            guild_id,
            'playlist_satisfaction',
            {'playlist_id': playlist_id, 'rating': rating}
        )

    def get_workflows_for_user(
        self,
        guild_id: int,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """Get all active workflows for a user in a guild.

        Args:
            guild_id: Discord guild (server) ID.
            user_id: Discord user ID.

        Returns:
            List of workflow dictionaries.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, guild_id, summary_message_id, original_channel_id,
                       song_matches, selections, message_ids, approver_ids,
                       setlist_data, status, expires_at, initiated_by, created_at
                FROM active_workflows
                WHERE guild_id = %s AND (
                    initiated_by = %s OR
                    approver_ids::jsonb ? %s
                )
                ORDER BY created_at DESC
            """, (guild_id, user_id, str(user_id)))
            return [dict(row) for row in cursor.fetchall()]

    def get_most_recent_workflow_for_user(
        self,
        guild_id: int,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent active workflow for a user in a guild.

        Args:
            guild_id: Discord guild (server) ID.
            user_id: Discord user ID.

        Returns:
            Workflow dictionary or None if not found.
        """
        workflows = self.get_workflows_for_user(guild_id, user_id)
        return workflows[0] if workflows else None

    def update_workflow_status(
        self,
        summary_message_id: int,
        status: str
    ) -> None:
        """Update workflow status.

        Args:
            summary_message_id: Workflow identifier.
            status: New status (pending, ready, completed, cancelled).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE active_workflows
                SET status = %s, updated_at = NOW()
                WHERE summary_message_id = %s
            """, (status, summary_message_id))
            logger.info(f"Updated workflow {summary_message_id} status to {status}")

    def get_expired_workflows(self) -> List[Dict[str, Any]]:
        """Get all workflows that have expired.

        Returns:
            List of expired workflow dictionaries.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, guild_id, summary_message_id, original_channel_id,
                       song_matches, selections, message_ids, approver_ids,
                       setlist_data, status, expires_at, initiated_by, created_at
                FROM active_workflows
                WHERE expires_at < NOW() AND status != 'completed'
                ORDER BY created_at ASC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_workflow_by_id(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        """Get workflow by database ID.

        Args:
            workflow_id: Database ID of the workflow.

        Returns:
            Workflow dictionary or None if not found.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT id, guild_id, summary_message_id, original_channel_id,
                       song_matches, selections, message_ids, approver_ids,
                       setlist_data, status, expires_at, initiated_by, created_at
                FROM active_workflows
                WHERE id = %s
            """, (workflow_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
