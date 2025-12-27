"""Main Discord bot implementation for Jambot."""
import discord
from discord.ext import commands
from typing import Optional, List, Dict, Any
import asyncio
from src.config import Config
from src.logger import logger
from src.database import Database
from src.spotify_client import SpotifyClient
from src.setlist_parser import SetlistParser
from src.commands import JambotCommands


class JamBot(commands.Bot):
    """Discord bot for managing bluegrass jam setlists and Spotify playlists."""

    # Emoji for approval workflow
    APPROVE_EMOJI = "✅"
    REJECT_EMOJI = "❌"
    SELECT_EMOJIS = ["1️⃣", "2️⃣", "3️⃣"]

    def __init__(self):
        """Initialize the jam bot."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True

        super().__init__(command_prefix='@jambot ', intents=intents)

        self.db = Database()
        self._default_parser = SetlistParser()
        self._guild_parsers: Dict[int, SetlistParser] = {}  # Cache guild-specific parsers
        self.commands_handler = JambotCommands(self, self.db)

        # Track active approval workflows
        self.active_workflows: Dict[int, Dict] = {}  # message_id -> workflow data

        logger.info("JamBot initialized")

    def get_parser_for_guild(self, guild_id: int) -> SetlistParser:
        """Get a parser configured with guild-specific patterns if available.

        Args:
            guild_id: Discord guild (server) ID.

        Returns:
            SetlistParser configured with guild's custom patterns or defaults.
        """
        # Check cache first
        if guild_id in self._guild_parsers:
            return self._guild_parsers[guild_id]

        # Get custom patterns from database
        patterns = self.db.get_setlist_patterns(guild_id)
        intro_pattern = patterns.get('intro_pattern')
        song_pattern = patterns.get('song_pattern')

        # If guild has custom patterns, create a custom parser
        if intro_pattern or song_pattern:
            parser = SetlistParser(
                intro_pattern=intro_pattern,
                song_pattern=song_pattern
            )
            self._guild_parsers[guild_id] = parser
            logger.info(f"Created custom parser for guild {guild_id}")
            return parser

        # Otherwise use default parser
        return self._default_parser

    def invalidate_parser_cache(self, guild_id: int):
        """Invalidate the cached parser for a guild (after pattern update).

        Args:
            guild_id: Discord guild (server) ID.
        """
        if guild_id in self._guild_parsers:
            del self._guild_parsers[guild_id]
            logger.info(f"Invalidated parser cache for guild {guild_id}")

    @property
    def parser(self) -> SetlistParser:
        """Default parser property for backwards compatibility."""
        return self._default_parser

    async def setup_hook(self):
        """Called when the bot is setting up."""
        # Register slash commands
        await self.commands_handler.setup()

        # Sync commands with Discord
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}", exc_info=True)

        logger.info("Bot setup complete")

    async def on_connect(self):
        """Called when the bot establishes a connection to Discord."""
        logger.info("Successfully connected to Discord Gateway")

    async def on_ready(self):
        """Called when the bot successfully connects to Discord."""
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info("Bot is ready. Use /jambot-setup to configure jam leaders and approvers in each server.")

    async def on_disconnect(self):
        """Called when the bot disconnects from Discord."""
        logger.warning("Disconnected from Discord")

    async def on_error(self, event, *args, **kwargs):
        """Called when an error occurs."""
        logger.error(f"Error in event {event}", exc_info=True)

    async def on_message(self, message: discord.Message):
        """Handle incoming messages.

        Args:
            message: Discord message object.
        """
        # Ignore bot's own messages
        if message.author.id == self.user.id:
            return

        # Handle DM messages (for manual song selection)
        if not message.guild:
            await self.handle_dm_message(message)
            return

        # Log all messages for debugging
        logger.info(f"Received message from {message.author} (ID: {message.author.id})")
        logger.info(f"Message content preview: {message.content[:100]}...")

        # Get guild-specific parser (with custom patterns if configured)
        parser = self.get_parser_for_guild(message.guild.id)

        # Check if message is from a jam leader
        if self.db.is_jam_leader(message.guild.id, message.author.id):
            if parser.is_setlist_message(message.content):
                logger.info(f"Detected setlist message from jam leader in channel {message.channel.id}")
                await self.handle_setlist_message(message)

        # Also fall back to env var for backwards compatibility during migration
        elif Config.DISCORD_JAM_LEADER_ID and str(message.author.id) == Config.DISCORD_JAM_LEADER_ID:
            if parser.is_setlist_message(message.content):
                logger.info(f"Detected setlist message from jam leader (env var) in channel {message.channel.id}")
                await self.handle_setlist_message(message)

        # Process commands
        await self.process_commands(message)

    async def handle_dm_message(self, message: discord.Message):
        """Handle DM messages for manual song selection.

        Allows users to reply to song embed messages with Spotify URLs
        to manually specify a track instead of using bot suggestions.

        Args:
            message: Discord DM message object.
        """
        try:
            logger.info(f"Received DM from {message.author} (ID: {message.author.id})")
            logger.info(f"DM content: {message.content[:200]}")

            # Check if message is a reply to one of our embeds
            if not message.reference or not message.reference.message_id:
                logger.info("DM is not a reply to another message")
                return

            replied_msg_id = message.reference.message_id
            logger.info(f"DM is a reply to message ID: {replied_msg_id}")

            # Find which workflow this message belongs to
            workflow_id = None
            song_number = None

            logger.info(f"Searching through {len(self.active_workflows)} active workflows")
            for wf_id, workflow in self.active_workflows.items():
                logger.info(f"  Workflow {wf_id} has {len(workflow['message_ids'])} messages")
                if replied_msg_id in workflow['message_ids']:
                    workflow_id = wf_id
                    # Find which song this message corresponds to
                    msg_index = workflow['message_ids'].index(replied_msg_id)
                    if msg_index < len(workflow['song_matches']):
                        song_number = workflow['song_matches'][msg_index]['number']
                    logger.info(f"Found workflow {wf_id} for song {song_number}")
                    break

            if not workflow_id or song_number is None:
                logger.info(f"DM reply not associated with any active workflow")
                logger.info(f"  Replied message ID: {replied_msg_id}")
                logger.info(f"  Active workflow IDs: {list(self.active_workflows.keys())}")
                return

            # Parse Spotify URL from message content
            spotify_url = None
            for word in message.content.split():
                if 'spotify.com/track/' in word or 'open.spotify.com/track/' in word:
                    spotify_url = word.strip('<>')  # Remove Discord's angle brackets
                    break

            if not spotify_url:
                await message.reply(
                    "❌ Please provide a Spotify track URL.\n"
                    "Example: `https://open.spotify.com/track/...`"
                )
                return

            # Validate and get track info
            logger.info(f"User provided manual Spotify URL for song {song_number}: {spotify_url}")

            # Get guild_id from workflow
            workflow = self.active_workflows[workflow_id]
            guild_id = workflow.get('guild_id', 0)

            # Create Spotify client for this guild
            spotify = SpotifyClient(guild_id=guild_id)
            track_info = spotify.get_track_from_url(spotify_url)

            if not track_info:
                await message.reply(
                    "❌ Invalid Spotify track URL or unable to fetch track information.\n"
                    "Please check the URL and try again."
                )
                return

            # Update workflow selection
            workflow = self.active_workflows[workflow_id]
            workflow['selections'][song_number] = track_info

            logger.info(
                f"Updated song {song_number} with manual selection: "
                f"{track_info['name']} by {track_info['artist']}"
            )

            # Send confirmation
            await message.reply(
                f"✅ **Manual selection confirmed!**\n"
                f"Song #{song_number}: [{track_info['name']}]({track_info['url']})\n"
                f"Artist: {track_info['artist']}\n"
                f"Album: {track_info['album']}"
            )

        except Exception as e:
            logger.error(f"Error handling DM message: {e}", exc_info=True)
            await message.reply(
                "❌ An error occurred while processing your request. "
                "Please try again or contact an administrator."
            )

    async def handle_setlist_message(self, message: discord.Message, triggered_by_user_id: int = None):
        """Process a detected setlist message.

        Args:
            message: Discord message containing the setlist.
            triggered_by_user_id: Optional user ID who triggered this manually (for /jambot-process).
        """
        try:
            # Get guild-specific parser (with custom patterns if configured)
            guild_id = message.guild.id if message.guild else 0
            parser = self.get_parser_for_guild(guild_id)

            # Parse the setlist
            setlist_data = parser.parse_setlist(message.content)
            if not setlist_data:
                logger.error(
                    "Failed to parse setlist message. The message was detected as a setlist "
                    "but couldn't be parsed. Check if the format matches the expected patterns."
                )
                await self.notify_admin(
                    f"⚠️ Failed to parse setlist message from {message.jump_url}\n"
                    f"The intro was detected but songs couldn't be extracted.\n"
                    f"Use `/jambot-learn-patterns` to configure custom setlist patterns for your server.",
                    guild_id=guild_id
                )
                return

            # Search for songs on Spotify and check database
            guild_id = message.guild.id if message.guild else 0
            song_matches = await self.find_song_matches(setlist_data['songs'], guild_id)

            # Send approval workflow to admin
            await self.send_approval_workflow(
                setlist_data=setlist_data,
                song_matches=song_matches,
                original_channel_id=message.channel.id,
                guild_id=guild_id,
                triggered_by_user_id=triggered_by_user_id
            )

        except Exception as e:
            logger.error(f"Error handling setlist message: {e}", exc_info=True)
            await self.notify_admin(
                f"❌ Error processing setlist: {e}",
                guild_id=message.guild.id if message.guild else None
            )

    async def find_song_matches(self, songs: List[Dict], guild_id: int) -> List[Dict[str, Any]]:
        """Find Spotify matches for a list of songs within a specific guild.

        Args:
            songs: List of song dictionaries with 'title' and 'number'.
            guild_id: Discord guild (server) ID.

        Returns:
            List of match dictionaries with song info and Spotify results.
        """
        matches = []

        # Create Spotify client for this guild
        spotify = SpotifyClient(guild_id=guild_id)

        for song in songs:
            song_title = song['title']
            logger.info(f"Searching for song in guild {guild_id}: {song_title}")

            # Check database first (guild-scoped)
            db_song = self.db.get_song_by_title(guild_id, song_title)
            if db_song:
                logger.info(f"Found stored version for: {song_title}")
                match = {
                    'number': song['number'],
                    'title': song_title,
                    'stored_version': {
                        'id': db_song['spotify_track_id'],
                        'name': db_song['spotify_track_name'],
                        'artist': db_song['artist'],
                        'album': db_song['album'],
                        'url': db_song['spotify_url'],
                        'uri': f"spotify:track:{db_song['spotify_track_id']}",
                    },
                    'spotify_results': [],
                }
            else:
                # Search Spotify
                spotify_results = spotify.search_song(song_title, limit=3)
                logger.info(f"Spotify search returned {len(spotify_results)} results")
                match = {
                    'number': song['number'],
                    'title': song_title,
                    'stored_version': None,
                    'spotify_results': spotify_results,
                }

            matches.append(match)

        return matches

    async def send_approval_workflow(
        self,
        setlist_data: Dict,
        song_matches: List[Dict],
        original_channel_id: int,
        guild_id: int,
        triggered_by_user_id: int = None
    ):
        """Send approval workflow DM to all configured approvers.

        Args:
            setlist_data: Parsed setlist data.
            song_matches: List of song matches from database/Spotify.
            original_channel_id: ID of channel where setlist was posted.
            guild_id: Discord guild (server) ID.
            triggered_by_user_id: Optional user ID who triggered this (will also receive workflow).
        """
        try:

            # Get approver IDs from database
            approver_ids = self.db.get_approver_ids(guild_id)
            logger.info(f"Approver IDs from database for guild {guild_id}: {approver_ids}")

            # Fall back to env var if no approvers configured
            if not approver_ids and Config.DISCORD_ADMIN_ID:
                approver_ids = [int(Config.DISCORD_ADMIN_ID)]
                logger.info("Using fallback admin from environment variable")

            # If triggered manually, ensure that user also gets the workflow
            if triggered_by_user_id and triggered_by_user_id not in approver_ids:
                approver_ids = list(approver_ids) + [triggered_by_user_id]
                logger.info(f"Added triggering user {triggered_by_user_id} to approver list")

            if not approver_ids:
                logger.error(
                    "No approvers configured for this guild. "
                    "Use /jambot-setup to add approvers who can approve Spotify playlists."
                )
                return

            logger.info(f"Sending approval workflow to {len(approver_ids)} user(s): {approver_ids}")

            # Send workflow to all approvers
            for approver_id in approver_ids:
                try:
                    await self._send_approval_workflow_to_user(
                        approver_id,
                        setlist_data,
                        song_matches,
                        original_channel_id,
                        guild_id
                    )
                except Exception as e:
                    logger.error(f"Failed to send approval workflow to user {approver_id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error sending approval workflow: {e}", exc_info=True)

    async def _send_approval_workflow_to_user(
        self,
        user_id: int,
        setlist_data: Dict,
        song_matches: List[Dict],
        original_channel_id: int,
        guild_id: int = 0
    ):
        """Send approval workflow DM to a specific user.

        Args:
            user_id: Discord user ID to send workflow to.
            setlist_data: Parsed setlist data.
            song_matches: List of song matches from database/Spotify.
            original_channel_id: ID of channel where setlist was posted.
            guild_id: Discord guild (server) ID.
        """
        # Get user
        user = await self.fetch_user(user_id)
        if not user:
            logger.error(
                f"Could not find user {user_id}. "
                f"User may have left the server or bot lacks permissions. "
                f"Use /jambot-setup to update approvers."
            )
            return

        # Create DM channel
        dm_channel = await user.create_dm()

        # Build approval message
        embed = discord.Embed(
            title=f"🎵 Setlist Approval: {setlist_data['time']} jam on {setlist_data['date']}",
            description="Please review and approve the song selections below.",
            color=discord.Color.blue()
        )

        # Track selections for this workflow
        workflow_data = {
            'setlist_data': setlist_data,
            'song_matches': song_matches,
            'original_channel_id': original_channel_id,
            'guild_id': guild_id,  # Store guild_id for DM handlers
            'selections': {},  # song_number -> track_info
            'message_ids': [],  # DM message IDs for reaction tracking
        }

        # Send song-by-song for approval
        for match in song_matches:
            song_embed = await self.create_song_approval_embed(match)
            msg = await dm_channel.send(embed=song_embed)
            workflow_data['message_ids'].append(msg.id)

            # Add reaction emojis based on options
            if match['stored_version']:
                # Pre-approved version - just add checkmark
                await msg.add_reaction(self.APPROVE_EMOJI)
                # Auto-select stored version
                workflow_data['selections'][match['number']] = match['stored_version']
            elif len(match['spotify_results']) == 0:
                # No matches - add X emoji
                await msg.add_reaction(self.REJECT_EMOJI)
            elif len(match['spotify_results']) == 1:
                # Single match - add checkmark to confirm
                await msg.add_reaction(self.APPROVE_EMOJI)
                # Auto-select the single result
                workflow_data['selections'][match['number']] = match['spotify_results'][0]
            else:
                # Multiple matches - add number emojis
                for i in range(min(len(match['spotify_results']), 3)):
                    await msg.add_reaction(self.SELECT_EMOJIS[i])

        # Send summary and final approval message
        summary_msg = await dm_channel.send(
            "✅ **Review complete! React with ✅ to create the playlist or ❌ to cancel.**"
        )
        await summary_msg.add_reaction(self.APPROVE_EMOJI)
        await summary_msg.add_reaction(self.REJECT_EMOJI)

        workflow_data['summary_message_id'] = summary_msg.id

        # Store workflow data
        for msg_id in workflow_data['message_ids'] + [summary_msg.id]:
            self.active_workflows[msg_id] = workflow_data

        logger.info(f"Sent approval workflow to user {user_id} for {len(song_matches)} songs")

    async def create_song_approval_embed(self, match: Dict) -> discord.Embed:
        """Create an embed for song approval.

        Args:
            match: Song match dictionary.

        Returns:
            Discord embed for the song.
        """
        song_num = match['number']
        song_title = match['title']

        if match['stored_version']:
            # Stored version
            track = match['stored_version']
            embed = discord.Embed(
                title=f"{song_num}. {song_title}",
                description=f"✅ **Stored Version (Pre-approved)**",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Track",
                value=f"[{track['name']}]({track['url']})\n{track['url']}",
                inline=False
            )
            embed.add_field(name="Artist", value=track['artist'], inline=True)
            embed.add_field(name="Album", value=track['album'], inline=True)

        elif not match['spotify_results']:
            # No matches
            embed = discord.Embed(
                title=f"{song_num}. {song_title}",
                description="❌ **No matches found**\nReply with Spotify track link to add manually.",
                color=discord.Color.red()
            )

        elif len(match['spotify_results']) == 1:
            # Single match
            track = match['spotify_results'][0]
            embed = discord.Embed(
                title=f"{song_num}. {song_title}",
                description=f"✅ **1 match found - React to approve**",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Track",
                value=f"[{track['name']}]({track['url']})\n{track['url']}",
                inline=False
            )
            embed.add_field(name="Artist", value=track['artist'], inline=True)
            embed.add_field(name="Album", value=track['album'], inline=True)

        else:
            # Multiple matches
            embed = discord.Embed(
                title=f"{song_num}. {song_title}",
                description=f"🎵 **{len(match['spotify_results'])} matches found - React to select**",
                color=discord.Color.gold()
            )
            for i, track in enumerate(match['spotify_results'][:5]):
                embed.add_field(
                    name=f"{self.SELECT_EMOJIS[i]} Option {i + 1}",
                    value=f"[{track['name']}]({track['url']})\n{track['artist']} - {track['album']}\n{track['url']}",
                    inline=False
                )

        return embed

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User):
        """Handle reaction additions for approval workflow.

        Args:
            reaction: Discord reaction object.
            user: User who added the reaction.
        """
        # Ignore bot's own reactions
        if user.id == self.user.id:
            return

        # Check if reaction is on an active workflow message
        if reaction.message.id not in self.active_workflows:
            return

        workflow = self.active_workflows[reaction.message.id]

        # Check if this is the summary message
        if reaction.message.id == workflow.get('summary_message_id'):
            if str(reaction.emoji) == self.APPROVE_EMOJI:
                await self.create_playlist_from_workflow(workflow)
            elif str(reaction.emoji) == self.REJECT_EMOJI:
                await reaction.message.channel.send("❌ Playlist creation cancelled.")
                self.cleanup_workflow(workflow)
            return

        # Handle song selection reactions
        # Find which song this message corresponds to
        msg_index = workflow['message_ids'].index(reaction.message.id)
        match = workflow['song_matches'][msg_index]

        emoji_str = str(reaction.emoji)

        if emoji_str in self.SELECT_EMOJIS:
            # Multiple choice selection
            idx = self.SELECT_EMOJIS.index(emoji_str)
            if idx < len(match['spotify_results']):
                workflow['selections'][match['number']] = match['spotify_results'][idx]
                logger.info(f"Admin selected option {idx + 1} for song {match['number']}")
                await reaction.message.channel.send(
                    f"✅ Selected option {idx + 1} for **{match['title']}**"
                )

    async def create_playlist_from_workflow(self, workflow: Dict):
        """Create Spotify playlist from approved workflow.

        Args:
            workflow: Workflow data dictionary.
        """
        try:
            setlist_data = workflow['setlist_data']
            selections = workflow['selections']

            # Verify all songs have selections (except rejected ones)
            missing_songs = []
            for match in workflow['song_matches']:
                if match['number'] not in selections and len(match['spotify_results']) > 0:
                    missing_songs.append(match['title'])

            if missing_songs:
                # Get approvers from database using guild_id from workflow
                guild_id = workflow.get('guild_id')
                approver_ids = self.db.get_approver_ids(guild_id) if guild_id else []

                # Fall back to env var if no approvers configured
                if not approver_ids and Config.DISCORD_ADMIN_ID:
                    approver_ids = [int(Config.DISCORD_ADMIN_ID)]

                error_message = (
                    f"⚠️ **Cannot create playlist** - Missing selections for:\n" +
                    "\n".join(f"- {song}" for song in missing_songs) +
                    "\n\n**To fix:** Select the missing songs above using the number reactions (1️⃣, 2️⃣, 3️⃣), "
                    "then remove your ✅ reaction from the summary message and add it again."
                )

                if approver_ids:
                    # Notify the first approver about the issue
                    admin = await self.fetch_user(approver_ids[0])
                    dm_channel = await admin.create_dm()
                    await dm_channel.send(error_message)
                else:
                    logger.error(f"Cannot notify about missing songs - no approvers configured: {missing_songs}")
                return

            # Get guild configuration for playlist name and channel
            channel = self.get_channel(workflow['original_channel_id'])
            guild_id = channel.guild.id if channel and hasattr(channel, 'guild') else None

            # Get configuration to determine playlist name and target channel
            config = self.db.get_bot_configuration(guild_id) if guild_id else None

            # Determine playlist name from template or use default
            if config and config.get('playlist_name_template'):
                playlist_name = config['playlist_name_template'].format(
                    date=setlist_data['date'],
                    time=setlist_data['time']
                )
            else:
                playlist_name = f"Bluegrass Jam {setlist_data['date']}"

            # Determine target channel - use configured channel if set, otherwise original
            target_channel_id = workflow['original_channel_id']
            if config and config.get('channel_id'):
                target_channel_id = config['channel_id']
                logger.info(f"Using configured channel {target_channel_id} for playlist posting")

            # Create setlist in database
            setlist_id = self.db.create_setlist(
                guild_id=guild_id or 0,
                date=setlist_data['date'],
                time=setlist_data['time'],
                playlist_name=playlist_name
            )

            # Prepare track URIs and update database
            track_uris = []
            for song_num in sorted(selections.keys()):
                track = selections[song_num]

                # Find original song title from matches
                song_title = next(
                    m['title'] for m in workflow['song_matches']
                    if m['number'] == song_num
                )

                # Add/update song in database
                song_id = self.db.add_or_update_song(
                    guild_id=guild_id or 0,
                    song_title=song_title,
                    spotify_track_id=track['id'],
                    spotify_track_name=track['name'],
                    artist=track['artist'],
                    album=track['album'],
                    spotify_url=track['url']
                )

                # Link song to setlist
                self.db.add_setlist_song(setlist_id, song_id, position=song_num)

                # Add to playlist
                track_uris.append(track['uri'])

            # Create Spotify client for this guild
            spotify = SpotifyClient(guild_id=guild_id)

            # Create Spotify playlist
            playlist_info = spotify.create_playlist(
                name=playlist_name,
                description=f"Bluegrass jam setlist for {setlist_data['time']} on {setlist_data['date']}",
                public=True
            )

            # Add tracks
            spotify.add_tracks_to_playlist(playlist_info['id'], track_uris)

            # Update database with playlist info
            self.db.update_setlist_playlist(
                setlist_id,
                playlist_info['id'],
                playlist_info['url']
            )

            # Post to target channel
            target_channel = self.get_channel(target_channel_id)
            if target_channel:
                await target_channel.send(
                    f"🎵 **Playlist created!**\n"
                    f"**{playlist_name}**\n"
                    f"{playlist_info['url']}\n"
                    f"({len(track_uris)} songs)"
                )

            # Notify approvers
            await self.notify_admin(
                f"✅ **Playlist created successfully!**\n"
                f"{playlist_info['url']}\n"
                f"Posted to <#{target_channel_id}>",
                guild_id=guild_id
            )

            logger.info(f"Successfully created playlist: {playlist_name}")

        except Exception as e:
            logger.error(f"Error creating playlist: {e}", exc_info=True)
            # Try to get guild_id for notification
            channel = self.get_channel(workflow.get('original_channel_id')) if workflow else None
            guild_id = channel.guild.id if channel and hasattr(channel, 'guild') else None
            await self.notify_admin(f"❌ Failed to create playlist: {e}", guild_id=guild_id)
        finally:
            # Always cleanup workflow to prevent memory leaks
            self.cleanup_workflow(workflow)

    def cleanup_workflow(self, workflow: Dict):
        """Clean up a completed or cancelled workflow.

        Args:
            workflow: Workflow data dictionary.
        """
        # Remove from active workflows
        for msg_id in workflow['message_ids'] + [workflow.get('summary_message_id')]:
            if msg_id in self.active_workflows:
                del self.active_workflows[msg_id]

        logger.info("Cleaned up workflow")

    async def notify_admin(self, message: str, guild_id: int = None):
        """Send a notification message to all configured approvers.

        Args:
            message: Message to send.
            guild_id: Optional guild ID to get approvers for. If None, uses fallback admin.
        """
        try:
            approver_ids = []

            # Try to get approvers from database if guild_id provided
            if guild_id:
                approver_ids = self.db.get_approver_ids(guild_id)

            # Fall back to env var if no approvers configured
            if not approver_ids and Config.DISCORD_ADMIN_ID:
                approver_ids = [int(Config.DISCORD_ADMIN_ID)]
                logger.info("Using fallback admin from environment variable")

            if not approver_ids:
                logger.warning(
                    "No approvers configured - cannot send notification. "
                    "Use /jambot-setup to add approvers."
                )
                return

            # Send to all approvers
            for approver_id in approver_ids:
                try:
                    user = await self.fetch_user(approver_id)
                    if user:
                        dm_channel = await user.create_dm()
                        await dm_channel.send(message)
                except Exception as e:
                    logger.error(f"Failed to notify user {approver_id}: {e}")

        except Exception as e:
            logger.error(f"Failed to notify approvers: {e}")
