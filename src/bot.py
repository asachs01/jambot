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
        self.spotify = SpotifyClient()
        self.parser = SetlistParser()

        # Track active approval workflows
        self.active_workflows: Dict[int, Dict] = {}  # message_id -> workflow data

        logger.info("JamBot initialized")

    async def setup_hook(self):
        """Called when the bot is setting up."""
        logger.info("Bot setup complete")

    async def on_ready(self):
        """Called when the bot successfully connects to Discord."""
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Monitoring messages from jam leader: {Config.DISCORD_JAM_LEADER_ID}")

    async def on_message(self, message: discord.Message):
        """Handle incoming messages.

        Args:
            message: Discord message object.
        """
        # Ignore bot's own messages
        if message.author.id == self.user.id:
            return

        # Check if message is from jam leader
        if str(message.author.id) == Config.DISCORD_JAM_LEADER_ID:
            if self.parser.is_setlist_message(message.content):
                logger.info(f"Detected setlist message from jam leader in channel {message.channel.id}")
                await self.handle_setlist_message(message)

        # Process commands
        await self.process_commands(message)

    async def handle_setlist_message(self, message: discord.Message):
        """Process a detected setlist message.

        Args:
            message: Discord message containing the setlist.
        """
        try:
            # Parse the setlist
            setlist_data = self.parser.parse_setlist(message.content)
            if not setlist_data:
                logger.error("Failed to parse setlist message")
                await self.notify_admin(f"⚠️ Failed to parse setlist message from {message.jump_url}")
                return

            # Search for songs on Spotify and check database
            song_matches = await self.find_song_matches(setlist_data['songs'])

            # Send approval workflow to admin
            await self.send_approval_workflow(
                setlist_data=setlist_data,
                song_matches=song_matches,
                original_channel_id=message.channel.id
            )

        except Exception as e:
            logger.error(f"Error handling setlist message: {e}", exc_info=True)
            await self.notify_admin(f"❌ Error processing setlist: {e}")

    async def find_song_matches(self, songs: List[Dict]) -> List[Dict[str, Any]]:
        """Find Spotify matches for a list of songs.

        Args:
            songs: List of song dictionaries with 'title' and 'number'.

        Returns:
            List of match dictionaries with song info and Spotify results.
        """
        matches = []

        for song in songs:
            song_title = song['title']
            logger.info(f"Searching for song: {song_title}")

            # Check database first
            db_song = self.db.get_song_by_title(song_title)
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
                    },
                    'spotify_results': [],
                }
            else:
                # Search Spotify
                spotify_results = self.spotify.search_song(song_title, limit=3)
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
        original_channel_id: int
    ):
        """Send approval workflow DM to admin.

        Args:
            setlist_data: Parsed setlist data.
            song_matches: List of song matches from database/Spotify.
            original_channel_id: ID of channel where setlist was posted.
        """
        try:
            # Get admin user
            admin = await self.fetch_user(int(Config.DISCORD_ADMIN_ID))
            if not admin:
                logger.error("Could not find admin user")
                return

            # Create DM channel
            dm_channel = await admin.create_dm()

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

            logger.info(f"Sent approval workflow to admin for {len(song_matches)} songs")

        except Exception as e:
            logger.error(f"Error sending approval workflow: {e}", exc_info=True)
            await self.notify_admin(f"❌ Failed to send approval workflow: {e}")

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
                value=f"[{track['name']}]({track['url']})",
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
                value=f"[{track['name']}]({track['url']})",
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
            for i, track in enumerate(match['spotify_results'][:3]):
                embed.add_field(
                    name=f"{self.SELECT_EMOJIS[i]} Option {i + 1}",
                    value=f"[{track['name']}]({track['url']})\n{track['artist']} - {track['album']}",
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
                admin = await self.fetch_user(int(Config.DISCORD_ADMIN_ID))
                dm_channel = await admin.create_dm()
                await dm_channel.send(
                    f"⚠️ **Cannot create playlist** - Missing selections for:\n" +
                    "\n".join(f"- {song}" for song in missing_songs)
                )
                return

            # Create setlist in database
            playlist_name = f"Bluegrass Jam {setlist_data['date']}"
            setlist_id = self.db.create_setlist(
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

            # Create Spotify playlist
            playlist_info = self.spotify.create_playlist(
                name=playlist_name,
                description=f"Bluegrass jam setlist for {setlist_data['time']} on {setlist_data['date']}",
                public=True
            )

            # Add tracks
            self.spotify.add_tracks_to_playlist(playlist_info['id'], track_uris)

            # Update database with playlist info
            self.db.update_setlist_playlist(
                setlist_id,
                playlist_info['id'],
                playlist_info['url']
            )

            # Post to original channel
            channel = self.get_channel(workflow['original_channel_id'])
            if channel:
                await channel.send(
                    f"🎵 **Playlist created!**\n"
                    f"**{playlist_name}**\n"
                    f"{playlist_info['url']}\n"
                    f"({len(track_uris)} songs)"
                )

            # Notify admin
            admin = await self.fetch_user(int(Config.DISCORD_ADMIN_ID))
            dm_channel = await admin.create_dm()
            await dm_channel.send(
                f"✅ **Playlist created successfully!**\n"
                f"{playlist_info['url']}\n"
                f"Posted to <#{workflow['original_channel_id']}>"
            )

            logger.info(f"Successfully created playlist: {playlist_name}")

            # Cleanup workflow
            self.cleanup_workflow(workflow)

        except Exception as e:
            logger.error(f"Error creating playlist: {e}", exc_info=True)
            await self.notify_admin(f"❌ Failed to create playlist: {e}")

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

    async def notify_admin(self, message: str):
        """Send a notification message to the admin.

        Args:
            message: Message to send.
        """
        try:
            admin = await self.fetch_user(int(Config.DISCORD_ADMIN_ID))
            if admin:
                dm_channel = await admin.create_dm()
                await dm_channel.send(message)
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
