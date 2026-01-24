"""Database management for Jambot using PostgreSQL."""
import psycopg2
import psycopg2.extras
from datetime import datetime
from typing import Optional, List, Dict, Any
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

        CREATE TABLE IF NOT EXISTS approval_workflows (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            setlist_data JSONB NOT NULL,
            song_matches JSONB NOT NULL,
            selections JSONB NOT NULL DEFAULT '{}',
            original_channel_id BIGINT NOT NULL,
            message_ids JSONB NOT NULL DEFAULT '[]',
            summary_message_id BIGINT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_songs_guild_title ON songs(guild_id, song_title);
        CREATE INDEX IF NOT EXISTS idx_setlists_guild_date ON setlists(guild_id, date);
        CREATE INDEX IF NOT EXISTS idx_setlist_songs_setlist_id ON setlist_songs(setlist_id);
        CREATE INDEX IF NOT EXISTS idx_setlist_songs_song_id ON setlist_songs(song_id);
        CREATE INDEX IF NOT EXISTS idx_bot_configuration_guild_id ON bot_configuration(guild_id);
        CREATE INDEX IF NOT EXISTS idx_spotify_tokens_guild_id ON spotify_tokens(guild_id);
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
            UNIQUE(guild_id, title)
        );

        CREATE INDEX IF NOT EXISTS idx_approval_workflows_status ON approval_workflows(status);
        CREATE INDEX IF NOT EXISTS idx_approval_workflows_guild_user ON approval_workflows(guild_id, user_id);
        CREATE INDEX IF NOT EXISTS idx_approval_workflows_message_ids ON approval_workflows USING GIN (message_ids);
        CREATE INDEX IF NOT EXISTS idx_chord_charts_guild_title ON chord_charts(guild_id, title);
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

    # ==================== Workflow Persistence Methods ====================

    def create_workflow(
        self,
        guild_id: int,
        user_id: int,
        setlist_data: Dict[str, Any],
        song_matches: List[Dict[str, Any]],
        original_channel_id: int,
        selections: Dict[int, Any] = None,
        message_ids: List[int] = None,
        summary_message_id: int = None
    ) -> int:
        """Create a new approval workflow in the database.

        Args:
            guild_id: Discord guild (server) ID.
            user_id: Discord user ID who will receive the workflow.
            setlist_data: Setlist metadata (date, time, etc.).
            song_matches: List of song match dictionaries.
            original_channel_id: Channel where setlist was posted.
            selections: Optional dict of song selections.
            message_ids: Optional list of DM message IDs.
            summary_message_id: Optional summary message ID.

        Returns:
            Workflow database ID.
        """
        import json

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO approval_workflows
                   (guild_id, user_id, setlist_data, song_matches, selections,
                    original_channel_id, message_ids, summary_message_id, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                   RETURNING id""",
                (
                    guild_id,
                    user_id,
                    json.dumps(setlist_data),
                    json.dumps(song_matches),
                    json.dumps(selections or {}),
                    original_channel_id,
                    json.dumps(message_ids or []),
                    summary_message_id
                )
            )
            workflow_id = cursor.fetchone()[0]
            logger.info(f"Created workflow {workflow_id} for user {user_id} in guild {guild_id}")
            return workflow_id

    def update_workflow(
        self,
        workflow_id: int,
        selections: Dict[int, Any] = None,
        message_ids: List[int] = None,
        summary_message_id: int = None,
        status: str = None
    ):
        """Update an existing workflow.

        Args:
            workflow_id: Workflow database ID.
            selections: Optional updated selections dict.
            message_ids: Optional updated message IDs list.
            summary_message_id: Optional summary message ID.
            status: Optional new status ('pending', 'completed', 'cancelled').
        """
        import json

        updates = []
        params = []

        if selections is not None:
            updates.append("selections = %s")
            params.append(json.dumps(selections))
        if message_ids is not None:
            updates.append("message_ids = %s")
            params.append(json.dumps(message_ids))
        if summary_message_id is not None:
            updates.append("summary_message_id = %s")
            params.append(summary_message_id)
        if status is not None:
            updates.append("status = %s")
            params.append(status)

        if not updates:
            return

        updates.append("updated_at = NOW()")
        params.append(workflow_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE approval_workflows SET {', '.join(updates)} WHERE id = %s",
                params
            )
            logger.debug(f"Updated workflow {workflow_id}")

    def get_workflow_by_id(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        """Get a workflow by its database ID.

        Args:
            workflow_id: Workflow database ID.

        Returns:
            Workflow dictionary if found, None otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT * FROM approval_workflows WHERE id = %s",
                (workflow_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._parse_workflow_row(row)
            return None

    def get_workflow_by_message_id(self, message_id: int) -> Optional[Dict[str, Any]]:
        """Get a workflow that contains a specific message ID.

        Args:
            message_id: Discord message ID to search for.

        Returns:
            Workflow dictionary if found, None otherwise.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            # Search in message_ids array or summary_message_id
            cursor.execute(
                """SELECT * FROM approval_workflows
                   WHERE (message_ids @> %s OR summary_message_id = %s)
                   AND status = 'pending'""",
                (f'[{message_id}]', message_id)
            )
            row = cursor.fetchone()
            if row:
                return self._parse_workflow_row(row)
            return None

    def get_pending_workflows(self) -> List[Dict[str, Any]]:
        """Get all pending workflows.

        Returns:
            List of workflow dictionaries.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT * FROM approval_workflows WHERE status = 'pending' ORDER BY created_at"
            )
            return [self._parse_workflow_row(row) for row in cursor.fetchall()]

    def delete_workflow(self, workflow_id: int):
        """Delete a workflow from the database.

        Args:
            workflow_id: Workflow database ID.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM approval_workflows WHERE id = %s",
                (workflow_id,)
            )
            logger.info(f"Deleted workflow {workflow_id}")

    def mark_workflow_completed(self, workflow_id: int):
        """Mark a workflow as completed.

        Args:
            workflow_id: Workflow database ID.
        """
        self.update_workflow(workflow_id, status='completed')
        logger.info(f"Marked workflow {workflow_id} as completed")

    def mark_workflow_cancelled(self, workflow_id: int):
        """Mark a workflow as cancelled.

        Args:
            workflow_id: Workflow database ID.
        """
        self.update_workflow(workflow_id, status='cancelled')
        logger.info(f"Marked workflow {workflow_id} as cancelled")

    # ==================== Chord Chart Methods ====================

    def create_chord_chart(
        self,
        guild_id: int,
        title: str,
        keys: List[Dict[str, Any]],
        created_by: int,
        chart_title: Optional[str] = None,
        lyrics: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """Create or update a chord chart.

        Args:
            guild_id: Discord guild (server) ID.
            title: Song title.
            keys: List of key entry dicts.
            created_by: Discord user ID.
            chart_title: Optional abbreviated title.
            lyrics: Optional lyrics data.

        Returns:
            Chart database ID.
        """
        import json

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO chord_charts
                   (guild_id, title, chart_title, lyrics, keys, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (guild_id, title) DO UPDATE SET
                       chart_title = EXCLUDED.chart_title,
                       lyrics = EXCLUDED.lyrics,
                       keys = EXCLUDED.keys,
                       updated_at = NOW()
                   RETURNING id""",
                (
                    guild_id, title, chart_title,
                    json.dumps(lyrics) if lyrics else None,
                    json.dumps(keys),
                    created_by,
                )
            )
            chart_id = cursor.fetchone()[0]
            logger.info(f"Created/updated chord chart '{title}' for guild {guild_id}")
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

    def _parse_workflow_row(self, row: Dict) -> Dict[str, Any]:
        """Parse a workflow database row into a workflow dictionary.

        Args:
            row: Database row dictionary.

        Returns:
            Parsed workflow dictionary with proper types.
        """
        workflow = dict(row)

        # JSONB columns are automatically parsed by psycopg2, but ensure proper types
        # Convert integer keys in selections back from strings (JSON keys are always strings)
        if workflow.get('selections'):
            workflow['selections'] = {
                int(k): v for k, v in workflow['selections'].items()
            }
        else:
            workflow['selections'] = {}

        if not workflow.get('message_ids'):
            workflow['message_ids'] = []

        return workflow
