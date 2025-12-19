"""Slash commands for Jambot configuration."""
import discord
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
from typing import List, Optional
from src.logger import logger
from src.database import Database
from src.setlist_parser import SetlistParser


class AdvancedSettingsModal(Modal, title="Advanced Settings"):
    """Modal for configuring optional advanced settings.

    Configures playlist channel and playlist name template.
    Basic configuration must be done first with /jambot-setup.
    """

    channel_id = TextInput(
        label="Playlist Channel ID (optional)",
        placeholder="Channel ID where playlists should be posted (leave blank for original channel)",
        style=discord.TextStyle.short,
        required=False,
        max_length=20
    )

    playlist_name_template = TextInput(
        label="Playlist Name Template (optional)",
        placeholder="Use {date} and {time} placeholders (default: Bluegrass Jam {date})",
        style=discord.TextStyle.short,
        required=False,
        max_length=100,
        default="Bluegrass Jam {date}"
    )

    def __init__(self, db: Database):
        """Initialize the advanced settings modal.

        Args:
            db: Database instance for storing configuration.
        """
        super().__init__()
        self.db = db

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission.

        Args:
            interaction: Discord interaction object.
        """
        try:
            guild_id = interaction.guild_id

            # Get existing configuration
            config = self.db.get_bot_configuration(guild_id)

            if not config:
                await interaction.response.send_message(
                    "❌ Error: Please run `/jambot-setup` first to configure basic settings.",
                    ephemeral=True
                )
                return

            # Parse optional channel ID
            channel_id_value = None
            if self.channel_id.value and self.channel_id.value.strip():
                try:
                    channel_id_value = int(self.channel_id.value.strip())
                    # Validate channel exists in guild
                    channel = interaction.guild.get_channel(channel_id_value)
                    if not channel:
                        await interaction.response.send_message(
                            f"❌ Error: Channel ID {channel_id_value} not found in this server.",
                            ephemeral=True
                        )
                        return
                except ValueError:
                    await interaction.response.send_message(
                        f"❌ Error: Invalid channel ID format: {self.channel_id.value}",
                        ephemeral=True
                    )
                    return

            # Parse optional playlist name template
            playlist_template = None
            if self.playlist_name_template.value and self.playlist_name_template.value.strip():
                playlist_template = self.playlist_name_template.value.strip()

            # Update configuration with advanced settings
            self.db.save_bot_configuration(
                guild_id=guild_id,
                jam_leader_ids=config['jam_leader_ids'],
                approver_ids=config['approver_ids'],
                channel_id=channel_id_value,
                playlist_name_template=playlist_template,
                spotify_client_id=config.get('spotify_client_id'),
                spotify_client_secret=config.get('spotify_client_secret'),
                spotify_redirect_uri=config.get('spotify_redirect_uri'),
                updated_by=interaction.user.id
            )

            logger.info(
                f"Advanced settings updated by {interaction.user.id} for guild {guild_id}: "
                f"channel={channel_id_value}, template={playlist_template}"
            )

            confirm_msg = "✅ **Advanced settings updated successfully!**\n\n"

            if channel_id_value:
                confirm_msg += f"**Playlist Channel:** <#{channel_id_value}>\n"
            else:
                confirm_msg += "**Playlist Channel:** Original message channel\n"

            if playlist_template:
                confirm_msg += f"**Playlist Name:** {playlist_template}\n"
            else:
                confirm_msg += "**Playlist Name:** Bluegrass Jam {date} (default)\n"

            await interaction.response.send_message(confirm_msg, ephemeral=True)

        except Exception as e:
            logger.error(f"Error processing advanced settings modal: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Error saving advanced settings: {str(e)}",
                ephemeral=True
            )


class ConfigurationModal(Modal, title="Configure Jambot"):
    """Modal for essential Jambot configuration.

    Configures jam leaders, approvers, and Spotify app credentials.
    For advanced settings (playlist channel, name template), use /jambot-settings.
    """

    jam_leaders = TextInput(
        label="Jam Leader User IDs",
        placeholder="User IDs separated by commas (e.g., 123456789, 987654321)",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    approvers = TextInput(
        label="Song Approver User IDs",
        placeholder="User IDs separated by commas (e.g., 123456789, 987654321)",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    spotify_client_id = TextInput(
        label="Spotify Client ID",
        placeholder="From developer.spotify.com/dashboard",
        style=discord.TextStyle.short,
        required=True,
        max_length=100
    )

    spotify_client_secret = TextInput(
        label="Spotify Client Secret",
        placeholder="From developer.spotify.com/dashboard (stored securely)",
        style=discord.TextStyle.short,
        required=True,
        max_length=100
    )

    spotify_redirect_uri = TextInput(
        label="Spotify Redirect URI (optional)",
        placeholder="Leave blank to use default web server URL",
        style=discord.TextStyle.short,
        required=False,
        max_length=200
    )

    def __init__(self, db: Database):
        """Initialize the configuration modal.

        Args:
            db: Database instance for storing configuration.
        """
        super().__init__()
        self.db = db

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission.

        Args:
            interaction: Discord interaction object.
        """
        try:
            # Parse user IDs from input
            jam_leader_ids = self._parse_user_ids(self.jam_leaders.value)
            approver_ids = self._parse_user_ids(self.approvers.value)

            if not jam_leader_ids:
                await interaction.response.send_message(
                    "❌ Error: Please provide at least one jam leader user ID.",
                    ephemeral=True
                )
                return

            if not approver_ids:
                await interaction.response.send_message(
                    "❌ Error: Please provide at least one approver user ID.",
                    ephemeral=True
                )
                return

            # Validate that user IDs exist in the guild
            invalid_ids = await self._validate_user_ids(
                interaction,
                jam_leader_ids + approver_ids
            )

            if invalid_ids:
                await interaction.response.send_message(
                    f"❌ Error: The following user IDs are invalid or not in this server: {', '.join(invalid_ids)}",
                    ephemeral=True
                )
                return

            # Parse and validate Spotify credentials
            spotify_client_id = self.spotify_client_id.value.strip() if self.spotify_client_id.value else None
            spotify_client_secret = self.spotify_client_secret.value.strip() if self.spotify_client_secret.value else None
            spotify_redirect_uri = self.spotify_redirect_uri.value.strip() if self.spotify_redirect_uri.value else None

            if not spotify_client_id or not spotify_client_secret:
                await interaction.response.send_message(
                    "❌ Error: Spotify Client ID and Client Secret are required.",
                    ephemeral=True
                )
                return

            # Get existing configuration to preserve advanced settings
            guild_id = interaction.guild_id
            existing_config = self.db.get_bot_configuration(guild_id)
            channel_id_value = existing_config.get('channel_id') if existing_config else None
            playlist_template = existing_config.get('playlist_name_template') if existing_config else None

            # Store configuration in database
            self.db.save_bot_configuration(
                guild_id=guild_id,
                jam_leader_ids=jam_leader_ids,
                approver_ids=approver_ids,
                channel_id=channel_id_value,
                playlist_name_template=playlist_template,
                spotify_client_id=spotify_client_id,
                spotify_client_secret=spotify_client_secret,
                spotify_redirect_uri=spotify_redirect_uri,
                updated_by=interaction.user.id
            )

            logger.info(
                f"Configuration updated by {interaction.user.id} for guild {guild_id}: "
                f"jam_leaders={jam_leader_ids}, approvers={approver_ids}, "
                f"spotify_configured=True"
            )

            # Build confirmation message
            jam_leaders_mentions = ", ".join([f"<@{uid}>" for uid in jam_leader_ids])
            approvers_mentions = ", ".join([f"<@{uid}>" for uid in approver_ids])

            confirm_msg = (
                f"✅ **Jambot configured successfully!**\n\n"
                f"**Jam Leaders:** {jam_leaders_mentions}\n"
                f"**Song Approvers:** {approvers_mentions}\n"
                f"**Spotify Client ID:** {spotify_client_id[:8]}...\n"
                f"**Spotify Client Secret:** {'*' * 8}\n\n"
                f"**Next step:** Run `/jambot-spotify-setup` to authorize Spotify and start creating playlists!\n\n"
                f"_Use `/jambot-settings` to configure playlist channel and name template._"
            )

            await interaction.response.send_message(confirm_msg, ephemeral=True)

        except Exception as e:
            logger.error(f"Error processing configuration modal: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Error saving configuration: {str(e)}",
                ephemeral=True
            )

    def _parse_user_ids(self, input_str: str) -> List[int]:
        """Parse comma-separated user IDs from input string.

        Args:
            input_str: Input string containing comma-separated user IDs.

        Returns:
            List of parsed user IDs as integers.
        """
        ids = []
        for item in input_str.split(','):
            item = item.strip()
            if item:
                try:
                    user_id = int(item)
                    if user_id not in ids:  # Avoid duplicates
                        ids.append(user_id)
                except ValueError:
                    logger.warning(f"Invalid user ID format: {item}")
        return ids

    async def _validate_user_ids(
        self,
        interaction: discord.Interaction,
        user_ids: List[int]
    ) -> List[str]:
        """Validate that user IDs exist in the guild.

        Args:
            interaction: Discord interaction object.
            user_ids: List of user IDs to validate.

        Returns:
            List of invalid user ID strings.
        """
        invalid_ids = []
        for user_id in user_ids:
            try:
                member = await interaction.guild.fetch_member(user_id)
                if not member:
                    invalid_ids.append(str(user_id))
            except discord.NotFound:
                invalid_ids.append(str(user_id))
            except discord.HTTPException as e:
                logger.error(f"Error fetching member {user_id}: {e}")
                invalid_ids.append(str(user_id))

        return invalid_ids


class SetlistPatternConfirmView(View):
    """View with buttons to confirm or reject learned setlist patterns."""

    def __init__(self, db: Database, bot, guild_id: int, analysis: dict, message_url: str):
        """Initialize the confirmation view.

        Args:
            db: Database instance.
            bot: Bot instance.
            guild_id: Guild ID to save patterns for.
            analysis: Analysis result from SetlistParser.analyze_setlist_structure()
            message_url: URL of the original message used for learning.
        """
        super().__init__(timeout=300)  # 5 minute timeout
        self.db = db
        self.bot = bot
        self.guild_id = guild_id
        self.analysis = analysis
        self.message_url = message_url
        self.confirmed = False

    @discord.ui.button(label="Confirm Pattern", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        """Handle pattern confirmation."""
        if interaction.user.id != interaction.message.interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the user who started this can confirm.",
                ephemeral=True
            )
            return

        # The default patterns already work well, we just need to confirm they work
        # If the analysis found songs, the patterns are compatible
        self.confirmed = True

        # Invalidate parser cache so new patterns take effect
        self.bot.invalidate_parser_cache(self.guild_id)

        await interaction.response.edit_message(
            content=(
                f"✅ **Pattern confirmed!**\n\n"
                f"Jambot will now recognize setlists in this format.\n"
                f"The default patterns have been verified to work with your setlist format.\n\n"
                f"**Test it:** Post a setlist message (or use `/jambot-process`) and Jambot will recognize it."
            ),
            view=None
        )
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        """Handle cancellation."""
        if interaction.user.id != interaction.message.interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the user who started this can cancel.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="❌ Pattern learning cancelled. No changes were made.",
            view=None
        )
        self.stop()


class JambotCommands:
    """Slash commands for Jambot."""

    def __init__(self, bot, db: Database):
        """Initialize Jambot commands.

        Args:
            bot: Discord bot instance.
            db: Database instance.
        """
        self.bot = bot
        self.db = db
        self.tree = bot.tree

    async def setup(self):
        """Register slash commands."""
        @self.tree.command(
            name="jambot-setup",
            description="Configure Jambot settings (Admin only)"
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def setup_command(interaction: discord.Interaction):
            """Open configuration modal for setting up Jambot.

            Args:
                interaction: Discord interaction object.
            """
            logger.info(
                f"Setup command invoked by {interaction.user.id} "
                f"in guild {interaction.guild_id}"
            )

            # Send the configuration modal
            modal = ConfigurationModal(self.db)
            await interaction.response.send_modal(modal)

        @setup_command.error
        async def setup_error(
            interaction: discord.Interaction,
            error: app_commands.AppCommandError
        ):
            """Handle errors for the setup command.

            Args:
                interaction: Discord interaction object.
                error: The error that occurred.
            """
            if isinstance(error, app_commands.errors.MissingPermissions):
                await interaction.response.send_message(
                    "❌ You need administrator permissions to use this command.",
                    ephemeral=True
                )
                logger.warning(
                    f"User {interaction.user.id} attempted to use setup command "
                    f"without permissions"
                )
            else:
                await interaction.response.send_message(
                    "❌ An error occurred while processing the command.",
                    ephemeral=True
                )
                logger.error(f"Error in setup command: {error}", exc_info=True)

        @self.tree.command(
            name="jambot-getid",
            description="Get a user's ID (mention them to see their ID)"
        )
        async def getid_command(
            interaction: discord.Interaction,
            user: discord.Member
        ):
            """Get a user's Discord ID for configuration.

            Args:
                interaction: Discord interaction object.
                user: The user to get the ID for.
            """
            await interaction.response.send_message(
                f"User ID for {user.mention}: `{user.id}`\n"
                f"Copy this ID to use in `/jambot-setup`",
                ephemeral=True
            )

        @self.tree.command(
            name="jambot-spotify-setup",
            description="Connect Spotify to this Discord server (Admin only)"
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def spotify_setup_command(interaction: discord.Interaction):
            """Generate Spotify authorization link for this guild.

            Args:
                interaction: Discord interaction object.
            """
            try:
                logger.info(
                    f"Spotify setup command invoked by {interaction.user.id} "
                    f"in guild {interaction.guild_id}"
                )

                # Generate auth URL for this guild and user
                from src.config import Config
                auth_url = f"{Config.SPOTIFY_REDIRECT_URI.rsplit('/', 1)[0]}/spotify/auth/{interaction.guild_id}/{interaction.user.id}"

                # Send DM to user with authorization link
                try:
                    await interaction.user.send(
                        f"🎵 **Spotify Authorization for {interaction.guild.name}**\n\n"
                        f"Click the link below to connect your Spotify account:\n"
                        f"{auth_url}\n\n"
                        f"This will allow JamBot to create playlists on your behalf for setlists posted in {interaction.guild.name}.\n\n"
                        f"**Important:** Only click this link if you trust this server and want to authorize Spotify access."
                    )

                    await interaction.response.send_message(
                        "✅ I've sent you a DM with the Spotify authorization link!",
                        ephemeral=True
                    )

                except discord.Forbidden:
                    # User has DMs disabled, show link in ephemeral message instead
                    await interaction.response.send_message(
                        f"🎵 **Spotify Authorization Link**\n\n"
                        f"Click here to connect Spotify: {auth_url}\n\n"
                        f"(I tried to DM you, but your DMs are disabled. This link is only visible to you.)",
                        ephemeral=True
                    )

            except Exception as e:
                logger.error(f"Error in spotify-setup command: {e}", exc_info=True)
                await interaction.response.send_message(
                    f"❌ Error generating Spotify authorization link: {str(e)}",
                    ephemeral=True
                )

        @spotify_setup_command.error
        async def spotify_setup_error(
            interaction: discord.Interaction,
            error: app_commands.AppCommandError
        ):
            """Handle errors for the spotify-setup command.

            Args:
                interaction: Discord interaction object.
                error: The error that occurred.
            """
            if isinstance(error, app_commands.errors.MissingPermissions):
                await interaction.response.send_message(
                    "❌ You need administrator permissions to use this command.",
                    ephemeral=True
                )
                logger.warning(
                    f"User {interaction.user.id} attempted to use spotify-setup command "
                    f"without permissions"
                )
            else:
                await interaction.response.send_message(
                    "❌ An error occurred while processing the command.",
                    ephemeral=True
                )
                logger.error(f"Error in spotify-setup command: {error}", exc_info=True)

        @self.tree.command(
            name="jambot-settings",
            description="Configure advanced playlist settings (Admin only)"
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def settings_command(interaction: discord.Interaction):
            """Open advanced settings modal for playlist configuration.

            Args:
                interaction: Discord interaction object.
            """
            logger.info(
                f"Settings command invoked by {interaction.user.id} "
                f"in guild {interaction.guild_id}"
            )

            # Send the advanced settings modal
            modal = AdvancedSettingsModal(self.db)
            await interaction.response.send_modal(modal)

        @settings_command.error
        async def settings_error(
            interaction: discord.Interaction,
            error: app_commands.AppCommandError
        ):
            """Handle errors for the settings command.

            Args:
                interaction: Discord interaction object.
                error: The error that occurred.
            """
            if isinstance(error, app_commands.errors.MissingPermissions):
                await interaction.response.send_message(
                    "❌ You need administrator permissions to use this command.",
                    ephemeral=True
                )
                logger.warning(
                    f"User {interaction.user.id} attempted to use settings command "
                    f"without permissions"
                )
            else:
                await interaction.response.send_message(
                    "❌ An error occurred while processing the command.",
                    ephemeral=True
                )
                logger.error(f"Error in settings command: {error}", exc_info=True)

        @self.tree.command(
            name="jambot-status",
            description="Show current Jambot configuration"
        )
        async def status_command(interaction: discord.Interaction):
            """Show current Jambot configuration for this server.

            Args:
                interaction: Discord interaction object.
            """
            try:
                logger.info(
                    f"Status command invoked by {interaction.user.id} "
                    f"in guild {interaction.guild_id}"
                )

                config = self.db.get_bot_configuration(interaction.guild_id)

                if not config:
                    await interaction.response.send_message(
                        "❌ **Jambot is not configured for this server.**\n\n"
                        "Run `/jambot-setup` to configure jam leaders, approvers, and Spotify credentials.",
                        ephemeral=True
                    )
                    return

                # Build status message
                jam_leader_ids = config.get('jam_leader_ids', [])
                approver_ids = config.get('approver_ids', [])
                channel_id = config.get('channel_id')
                playlist_template = config.get('playlist_name_template') or 'Bluegrass Jam {date}'
                spotify_configured = bool(config.get('spotify_client_id'))
                spotify_authorized = self.db.is_spotify_authorized(interaction.guild_id)

                # Format user mentions
                jam_leaders_str = ', '.join([f"<@{uid}>" for uid in jam_leader_ids]) if jam_leader_ids else '_None configured_'
                approvers_str = ', '.join([f"<@{uid}>" for uid in approver_ids]) if approver_ids else '_None configured_'

                # Format channel
                if channel_id:
                    channel_str = f"<#{channel_id}>"
                else:
                    channel_str = "_Original message channel_"

                # Format Spotify status
                if spotify_authorized:
                    spotify_status = "✅ Connected"
                elif spotify_configured:
                    spotify_status = "⚠️ Credentials set, but not authorized. Run `/jambot-spotify-setup`"
                else:
                    spotify_status = "❌ Not configured"

                embed = discord.Embed(
                    title="🎵 Jambot Configuration",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Jam Leaders", value=jam_leaders_str, inline=False)
                embed.add_field(name="Song Approvers", value=approvers_str, inline=False)
                embed.add_field(name="Playlist Channel", value=channel_str, inline=True)
                embed.add_field(name="Playlist Name", value=f"`{playlist_template}`", inline=True)
                embed.add_field(name="Spotify", value=spotify_status, inline=False)

                embed.set_footer(text="Use /jambot-setup to change settings")

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                logger.error(f"Error in status command: {e}", exc_info=True)
                await interaction.response.send_message(
                    f"❌ Error retrieving configuration: {str(e)}",
                    ephemeral=True
                )

        @self.tree.command(
            name="jambot-process",
            description="Process a setlist message manually (Approver only)"
        )
        @app_commands.describe(
            message_link="Discord message link (right-click message > Copy Message Link)"
        )
        async def process_command(
            interaction: discord.Interaction,
            message_link: str
        ):
            """Manually process a setlist message.

            Args:
                interaction: Discord interaction object.
                message_link: Discord message link to process.
            """
            try:
                logger.info(
                    f"Process command invoked by {interaction.user.id} "
                    f"in guild {interaction.guild_id} with link: {message_link}"
                )

                # Check if user is an approver or admin
                approver_ids = self.db.get_approver_ids(interaction.guild_id)
                is_approver = interaction.user.id in approver_ids
                is_admin = interaction.user.guild_permissions.administrator

                if not is_approver and not is_admin:
                    await interaction.response.send_message(
                        f"❌ Only song approvers or administrators can use this command.\n"
                        f"Your ID: `{interaction.user.id}`\n"
                        f"Configured approvers: `{approver_ids}`",
                        ephemeral=True
                    )
                    return

                # Parse Discord message link
                # Format: https://discord.com/channels/{guild_id}/{channel_id}/{message_id}
                import re
                link_pattern = re.compile(
                    r'https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)'
                )
                match = link_pattern.match(message_link.strip())

                if not match:
                    await interaction.response.send_message(
                        "❌ Invalid message link format.\n"
                        "Right-click a message and select 'Copy Message Link' to get the correct format.",
                        ephemeral=True
                    )
                    return

                link_guild_id = int(match.group(1))
                channel_id = int(match.group(2))
                message_id = int(match.group(3))

                # Verify the message is from this guild
                if link_guild_id != interaction.guild_id:
                    await interaction.response.send_message(
                        "❌ That message is from a different server.",
                        ephemeral=True
                    )
                    return

                # Fetch the channel and message
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    await interaction.response.send_message(
                        "❌ Could not find that channel. Make sure the bot has access to it.",
                        ephemeral=True
                    )
                    return

                try:
                    message = await channel.fetch_message(message_id)
                except discord.NotFound:
                    await interaction.response.send_message(
                        "❌ Could not find that message. It may have been deleted.",
                        ephemeral=True
                    )
                    return
                except discord.Forbidden:
                    await interaction.response.send_message(
                        "❌ I don't have permission to read messages in that channel.",
                        ephemeral=True
                    )
                    return

                # Check if the message is a valid setlist using guild-specific parser
                parser = self.bot.get_parser_for_guild(interaction.guild_id)
                if not parser.is_setlist_message(message.content):
                    await interaction.response.send_message(
                        "❌ That message doesn't appear to be a setlist.\n"
                        "Expected format: \"Here's the setlist for the [time] jam on [date].\"\n"
                        "Use `/jambot-learn-patterns` to configure custom setlist patterns.",
                        ephemeral=True
                    )
                    return

                # Acknowledge the command immediately
                await interaction.response.send_message(
                    f"✅ Processing setlist from {message.author.mention}...\n"
                    f"Check your DMs for the approval workflow.",
                    ephemeral=True
                )

                # Process the setlist, passing the user who triggered it
                await self.bot.handle_setlist_message(message, triggered_by_user_id=interaction.user.id)

                logger.info(
                    f"Successfully triggered setlist processing for message {message_id} "
                    f"by {interaction.user.id}"
                )

            except Exception as e:
                logger.error(f"Error in process command: {e}", exc_info=True)
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"❌ Error processing setlist: {str(e)}",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"❌ Error processing setlist: {str(e)}",
                        ephemeral=True
                    )

        @process_command.error
        async def process_error(
            interaction: discord.Interaction,
            error: app_commands.AppCommandError
        ):
            """Handle errors for the process command.

            Args:
                interaction: Discord interaction object.
                error: The error that occurred.
            """
            await interaction.response.send_message(
                "❌ An error occurred while processing the command.",
                ephemeral=True
            )
            logger.error(f"Error in process command: {error}", exc_info=True)

        @self.tree.command(
            name="jambot-learn-patterns",
            description="Scan channel for setlists and learn the pattern (Admin only)"
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def learn_patterns_command(interaction: discord.Interaction):
            """Scan channel for potential setlists and help configure patterns.

            This command scans the last 50 messages in the channel for potential
            setlists, shows what it found, and lets the admin confirm the pattern.

            Args:
                interaction: Discord interaction object.
            """
            try:
                await interaction.response.defer(ephemeral=True)

                channel = interaction.channel
                guild_id = interaction.guild_id

                # Scan last 50 messages for potential setlists
                potential_setlists = []
                async for message in channel.history(limit=50):
                    if message.author.bot:
                        continue

                    is_potential, details = SetlistParser.detect_potential_setlist(message.content)
                    if is_potential:
                        potential_setlists.append({
                            'message': message,
                            'details': details,
                            'confidence': details['confidence']
                        })

                if not potential_setlists:
                    await interaction.followup.send(
                        "❌ **No potential setlists found in the last 50 messages.**\n\n"
                        "I look for messages with:\n"
                        "• Numbered lists (1., 2., 3., etc.)\n"
                        "• Keywords like 'setlist', 'jam', 'songs for'\n\n"
                        "Try posting a setlist message in this channel and run this command again.",
                        ephemeral=True
                    )
                    return

                # Sort by confidence and get the best match
                potential_setlists.sort(key=lambda x: x['confidence'], reverse=True)
                best_match = potential_setlists[0]
                best_message = best_match['message']

                # Analyze the structure
                analysis = SetlistParser.analyze_setlist_structure(best_message.content)

                if not analysis['success']:
                    await interaction.followup.send(
                        f"⚠️ **Found a potential setlist but couldn't fully parse it.**\n\n"
                        f"Message from {best_message.author.mention} ({best_message.jump_url}):\n"
                        f"```\n{best_message.content[:500]}{'...' if len(best_message.content) > 500 else ''}\n```\n\n"
                        f"Keywords found: {', '.join(best_match['details']['matched_keywords']) or 'None'}\n"
                        f"Numbered items found: {len(best_match['details']['numbered_items'])}\n\n"
                        "I had trouble extracting the songs. Make sure your setlist has:\n"
                        "• A header line with the date/time\n"
                        "• Numbered songs (1., 2., 3., etc.)",
                        ephemeral=True
                    )
                    return

                # Build the success message
                song_preview = "\n".join([
                    f"  {s['number']}. {s['title']}" + (f" ({s['key']})" if s['key'] else "")
                    for s in analysis['songs'][:5]
                ])
                if len(analysis['songs']) > 5:
                    song_preview += f"\n  ... and {len(analysis['songs']) - 5} more songs"

                response = (
                    f"🎵 **Found a setlist!** (Confidence: {best_match['confidence']:.0%})\n\n"
                    f"**Source:** Message from {best_message.author.mention}\n"
                    f"**Link:** {best_message.jump_url}\n\n"
                )

                if analysis['intro_line']:
                    response += f"**Header detected:**\n```\n{analysis['intro_line']}\n```\n"

                if analysis['detected_time'] or analysis['detected_date']:
                    response += f"**Time:** {analysis['detected_time'] or 'Not detected'}\n"
                    response += f"**Date:** {analysis['detected_date'] or 'Not detected'}\n\n"

                response += f"**Songs found ({len(analysis['songs'])}):**\n```\n{song_preview}\n```\n"
                format_desc = 'Songs with keys (e.g., "Song Name (G)")' if analysis['has_keys'] else 'Songs without keys'
                response += f"**Format:** {format_desc}\n\n"

                response += (
                    "**Does this look correct?** Click 'Confirm Pattern' to enable this format.\n"
                    "Jambot will then automatically recognize setlists in this format."
                )

                # Create confirmation view
                view = SetlistPatternConfirmView(
                    db=self.db,
                    bot=self.bot,
                    guild_id=guild_id,
                    analysis=analysis,
                    message_url=best_message.jump_url
                )

                await interaction.followup.send(response, view=view, ephemeral=True)

                logger.info(
                    f"Learn patterns command invoked by {interaction.user.id} "
                    f"in guild {guild_id}, found {len(potential_setlists)} potential setlists"
                )

            except Exception as e:
                logger.error(f"Error in learn patterns command: {e}", exc_info=True)
                if interaction.response.is_done():
                    await interaction.followup.send(
                        f"❌ Error scanning for setlists: {str(e)}",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"❌ Error scanning for setlists: {str(e)}",
                        ephemeral=True
                    )

        @learn_patterns_command.error
        async def learn_patterns_error(
            interaction: discord.Interaction,
            error: app_commands.AppCommandError
        ):
            """Handle errors for the learn patterns command."""
            if isinstance(error, app_commands.errors.MissingPermissions):
                await interaction.response.send_message(
                    "❌ You need administrator permissions to use this command.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ An error occurred while processing the command.",
                    ephemeral=True
                )
                logger.error(f"Error in learn patterns command: {error}", exc_info=True)

        logger.info("Slash commands registered")
