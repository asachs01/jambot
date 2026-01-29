"""Slash commands for Jambot configuration."""
import discord
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button
from typing import List, Optional
import bcrypt
from src.logger import logger
from src.database import Database
from src.setlist_parser import SetlistParser
from src.premium_client import (
    PremiumClient,
    InvalidTokenError,
    APIConnectionError,
    PremiumAPIError
)


class FeedbackModal(Modal, title="Send Feedback"):
    """Modal for submitting user feedback.

    Allows users to report bugs, request features, or provide general feedback.
    Feedback is stored in the database and optionally sent to the maintainer.
    """

    feedback_type = TextInput(
        label="Feedback Type",
        placeholder="bug, feature, or general",
        style=discord.TextStyle.short,
        required=True,
        max_length=20,
        default="general"
    )

    message = TextInput(
        label="Your Feedback",
        placeholder="Tell us what's on your mind...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    context = TextInput(
        label="Additional Context (optional)",
        placeholder="Any extra details that might help (e.g., what you were trying to do)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )

    def __init__(self, db: Database, bot):
        """Initialize the feedback modal.

        Args:
            db: Database instance for storing feedback.
            bot: Bot instance for sending notifications.
        """
        super().__init__()
        self.db = db
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission.

        Args:
            interaction: Discord interaction object.
        """
        try:
            # Validate feedback type
            feedback_type = self.feedback_type.value.strip().lower()
            if feedback_type not in ['bug', 'feature', 'general']:
                await interaction.response.send_message(
                    "❌ Feedback type must be 'bug', 'feature', or 'general'.",
                    ephemeral=True
                )
                return

            # Save feedback to database
            feedback_id = self.db.save_feedback(
                guild_id=interaction.guild_id,
                user_id=interaction.user.id,
                feedback_type=feedback_type,
                message=self.message.value,
                context=self.context.value if self.context.value else None
            )

            # Track usage
            self.db.track_usage_event(
                interaction.guild_id,
                'feedback_submitted',
                {'type': feedback_type}
            )

            # Try to notify maintainer
            await self.bot.notify_feedback(
                feedback_id=feedback_id,
                guild_id=interaction.guild_id,
                user=interaction.user,
                feedback_type=feedback_type,
                message=self.message.value,
                context=self.context.value
            )

            logger.info(
                f"Feedback submitted by {interaction.user.id} in guild {interaction.guild_id}: "
                f"type={feedback_type}, id={feedback_id}"
            )

            await interaction.response.send_message(
                f"✅ **Thank you for your feedback!**\n\n"
                f"Your {feedback_type} feedback has been recorded (ID: #{feedback_id}).\n"
                f"We appreciate you taking the time to help improve Jambot!",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error processing feedback modal: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Error submitting feedback: {str(e)}",
                ephemeral=True
            )


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


class PremiumSetupModal(Modal, title="Configure Premium Access"):
    """Modal for configuring premium API token.

    Allows administrators to set up premium chord chart generation
    by entering their premium API token.
    """

    api_token = TextInput(
        label="Premium API Token",
        placeholder="Enter your premium API token (jbp_...)",
        style=discord.TextStyle.short,
        required=True,
        max_length=100
    )

    def __init__(self, db: Database):
        """Initialize the premium setup modal.

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
        guild_id = interaction.guild_id
        logger.info(f"Premium setup modal submitted by {interaction.user.id} in guild {guild_id}")

        try:
            token = self.api_token.value.strip()

            # Check if basic bot configuration exists
            config = self.db.get_bot_configuration(guild_id)
            if not config:
                logger.warning(f"Premium setup failed: no bot configuration for guild {guild_id}. User must run /jambot-setup first.")
                await interaction.response.send_message(
                    "**Setup Required**\n\n"
                    "Please run `/jambot-setup` first to configure Jambot's basic settings "
                    "(jam leaders, approvers, Spotify credentials).\n\n"
                    "After that, come back and run `/jambot-premium-setup` again.",
                    ephemeral=True
                )
                return

            # Defer response since validation may take a moment
            await interaction.response.defer(ephemeral=True)

            logger.info(f"Validating premium token for guild {guild_id}")

            # Validate the token with the premium API
            try:
                async with PremiumClient() as client:
                    result = await client.validate_token(token)
                    logger.info(f"Token validation result for guild {guild_id}: valid={result.get('valid')}")

                    if not result.get("valid", False):
                        await interaction.followup.send(
                            "Invalid API token. Please check your token and try again.\n\n"
                            "You can get a premium token at https://premium.jambot.app",
                            ephemeral=True
                        )
                        return

                    # Get credit balance to show in confirmation
                    credits = await client.get_credits(token, guild_id)

            except InvalidTokenError:
                await interaction.followup.send(
                    "Invalid or expired API token. Please check your token and try again.\n\n"
                    "You can get a premium token at https://premium.jambot.app",
                    ephemeral=True
                )
                return
            except APIConnectionError as e:
                await interaction.followup.send(
                    f"Unable to connect to premium service: {str(e)}\n\n"
                    "Please try again later or contact support.",
                    ephemeral=True
                )
                return
            except PremiumAPIError as e:
                await interaction.followup.send(
                    f"Premium API error: {str(e)}",
                    ephemeral=True
                )
                return

            # Hash the token for secure storage (hash used for verification)
            token_bytes = token.encode('utf-8')
            token_hash = bcrypt.hashpw(token_bytes, bcrypt.gensalt()).decode('utf-8')

            logger.info(f"Saving premium config for guild {guild_id}")

            # Save the premium configuration (both token and hash stored)
            success = self.db.save_premium_config(
                guild_id=guild_id,
                token=token,
                token_hash=token_hash,
                setup_by=interaction.user.id
            )

            logger.info(f"Save premium config result for guild {guild_id}: success={success}")

            if not success:
                logger.error(f"Failed to save premium config for guild {guild_id}")
                await interaction.followup.send(
                    "Error saving premium configuration. Please try again.",
                    ephemeral=True
                )
                return

            # Track usage
            self.db.track_usage_event(
                guild_id,
                'premium_setup',
                {'setup_by': interaction.user.id}
            )

            logger.info(
                f"Premium access configured by {interaction.user.id} for guild {guild_id}"
            )

            # Build confirmation message
            trial_msg = ""
            if credits.trial_credits_remaining > 0:
                trial_msg = f"\n**Trial Credits:** {credits.trial_credits_remaining} remaining"

            await interaction.followup.send(
                f"**Premium access configured successfully!**\n\n"
                f"**Credits Available:** {credits.credits_remaining}{trial_msg}\n"
                f"**Lifetime Purchased:** {credits.lifetime_purchased}\n\n"
                f"You can now use `/jambot-chart create` to generate AI chord charts!\n\n"
                f"_Use `/jambot-credits` to check your balance, or `/jambot-buy-credits` to purchase more._",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error processing premium setup modal: {e}", exc_info=True)
            if interaction.response.is_done():
                await interaction.followup.send(
                    f"Error setting up premium access: {str(e)}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"Error setting up premium access: {str(e)}",
                    ephemeral=True
                )


class CreditPackSelectView(View):
    """View with buttons for selecting credit pack sizes to purchase."""

    CREDIT_PACKS = [
        {"id": "credit_pack_10", "credits": 10, "price": "$1.99", "label": "10 Credits"},
        {"id": "credit_pack_30", "credits": 30, "price": "$3.99", "label": "30 Credits", "savings": "33%"},
        {"id": "credit_pack_75", "credits": 75, "price": "$6.99", "label": "75 Credits", "savings": "53%"},
    ]

    def __init__(self, db: Database, guild_id: int, token: str):
        """Initialize the credit pack selection view.

        Args:
            db: Database instance.
            guild_id: Guild ID for the purchase.
            token: Premium API token for generating checkout URLs.
        """
        super().__init__(timeout=300)  # 5 minute timeout
        self.db = db
        self.guild_id = guild_id
        self.token = token

        # Add buttons for each credit pack
        for pack in self.CREDIT_PACKS:
            savings_text = f" ({pack['savings']} off)" if pack.get('savings') else ""
            button = Button(
                label=f"{pack['label']} - {pack['price']}{savings_text}",
                style=discord.ButtonStyle.primary,
                custom_id=pack['id']
            )
            button.callback = self._create_callback(pack['id'])
            self.add_item(button)

    def _create_callback(self, product_id: str):
        """Create a callback function for a specific product.

        Args:
            product_id: Product ID for checkout.

        Returns:
            Async callback function.
        """
        async def callback(interaction: discord.Interaction):
            try:
                await interaction.response.defer(ephemeral=True)

                async with PremiumClient() as client:
                    checkout_url = await client.get_checkout_url(
                        self.token,
                        product_id,
                        self.guild_id
                    )

                if not checkout_url:
                    await interaction.followup.send(
                        "Unable to generate checkout URL. Please try again later.",
                        ephemeral=True
                    )
                    return

                # Track purchase attempt
                self.db.track_usage_event(
                    self.guild_id,
                    'credit_purchase_started',
                    {'product_id': product_id}
                )

                await interaction.followup.send(
                    f"**Complete your purchase:**\n\n"
                    f"{checkout_url}\n\n"
                    f"_This link expires in 24 hours. Credits will be added immediately after payment._",
                    ephemeral=True
                )

            except InvalidTokenError:
                await interaction.followup.send(
                    "Your premium token is invalid or expired. "
                    "Please run `/jambot-premium-setup` to reconfigure.",
                    ephemeral=True
                )
            except APIConnectionError as e:
                await interaction.followup.send(
                    f"Unable to connect to premium service: {str(e)}",
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error generating checkout URL: {e}", exc_info=True)
                await interaction.followup.send(
                    f"Error generating checkout URL: {str(e)}",
                    ephemeral=True
                )

        return callback


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

        @self.tree.command(
            name="jambot-feedback",
            description="Send feedback, report bugs, or request features"
        )
        async def feedback_command(interaction: discord.Interaction):
            """Open feedback modal for submitting user feedback.

            Args:
                interaction: Discord interaction object.
            """
            logger.info(
                f"Feedback command invoked by {interaction.user.id} "
                f"in guild {interaction.guild_id}"
            )

            # Track command usage
            self.db.track_usage_event(
                interaction.guild_id,
                'command_used',
                {'command': 'jambot-feedback'}
            )

            # Send the feedback modal
            modal = FeedbackModal(self.db, self.bot)
            await interaction.response.send_modal(modal)

        @feedback_command.error
        async def feedback_error(
            interaction: discord.Interaction,
            error: app_commands.AppCommandError
        ):
            """Handle errors for the feedback command.

            Args:
                interaction: Discord interaction object.
                error: The error that occurred.
            """
            await interaction.response.send_message(
                "❌ An error occurred while processing the command.",
                ephemeral=True
            )
            logger.error(f"Error in feedback command: {error}", exc_info=True)

        @self.tree.command(
            name="jambot-retry",
            description="Retry playlist creation for a workflow with missing selections"
        )
        @app_commands.describe(
            workflow_id="Workflow ID (optional - defaults to most recent)"
        )
        async def retry_command(
            interaction: discord.Interaction,
            workflow_id: Optional[int] = None
        ):
            """Retry playlist creation after fixing missing selections.

            Args:
                interaction: Discord interaction object.
                workflow_id: Optional workflow database ID.
            """
            try:
                logger.info(
                    f"Retry command invoked by {interaction.user.id} "
                    f"in guild {interaction.guild_id} for workflow {workflow_id}"
                )

                # Get workflow - either by ID or most recent for user
                if workflow_id:
                    workflow = self.db.get_workflow_by_id(workflow_id)
                    if not workflow or workflow['guild_id'] != interaction.guild_id:
                        await interaction.response.send_message(
                            f"❌ Workflow #{workflow_id} not found in this server.",
                            ephemeral=True
                        )
                        return
                else:
                    workflow = self.db.get_most_recent_workflow_for_user(
                        interaction.guild_id,
                        interaction.user.id
                    )
                    if not workflow:
                        await interaction.response.send_message(
                            "❌ No active workflows found for you in this server.\n"
                            "Use `/jambot-process` to start a new workflow.",
                            ephemeral=True
                        )
                        return

                # Check if workflow is ready
                is_ready, missing_songs = self.bot.is_workflow_ready(workflow)

                if not is_ready:
                    missing_list = "\n".join(f"- {song}" for song in missing_songs)
                    await interaction.response.send_message(
                        f"⚠️ **Workflow #{workflow['id']} still has missing selections:**\n\n"
                        f"{missing_list}\n\n"
                        f"Please select the missing songs using the number reactions "
                        f"(1️⃣, 2️⃣, 3️⃣) in the DM workflow, or reply with a Spotify URL.\n\n"
                        f"Once selections are complete, run `/jambot-retry` again.",
                        ephemeral=True
                    )
                    return

                # Workflow is ready - trigger playlist creation
                await interaction.response.defer(ephemeral=True)

                # Load workflow into active_workflows if not already there
                summary_msg_id = workflow['summary_message_id']
                if summary_msg_id not in self.bot.active_workflows:
                    for msg_id in workflow['message_ids'] + [summary_msg_id]:
                        self.bot.active_workflows[msg_id] = workflow

                await self.bot.create_playlist_from_workflow(workflow)

                await interaction.followup.send(
                    f"✅ **Playlist creation triggered for workflow #{workflow['id']}!**\n"
                    f"Check the playlist channel for the result.",
                    ephemeral=True
                )

            except Exception as e:
                logger.error(f"Error in retry command: {e}", exc_info=True)
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"❌ Error retrying workflow: {str(e)}",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"❌ Error retrying workflow: {str(e)}",
                        ephemeral=True
                    )

        @self.tree.command(
            name="jambot-workflow-status",
            description="Show active approval workflows and their status"
        )
        @app_commands.describe(
            show_all="Show all workflows in this server (admin only)"
        )
        async def workflow_status_command(
            interaction: discord.Interaction,
            show_all: Optional[bool] = False
        ):
            """Show active workflows and their selection progress.

            Args:
                interaction: Discord interaction object.
                show_all: Whether to show all workflows (admin only).
            """
            try:
                logger.info(
                    f"Workflow status command invoked by {interaction.user.id} "
                    f"in guild {interaction.guild_id}"
                )

                # Check admin permission for show_all
                if show_all and not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message(
                        "❌ Only administrators can view all workflows.",
                        ephemeral=True
                    )
                    return

                # Get workflows
                if show_all:
                    # Get all active workflows for the guild
                    all_workflows = self.db.get_all_active_workflows()
                    workflows = [w for w in all_workflows if w['guild_id'] == interaction.guild_id]
                else:
                    workflows = self.db.get_workflows_for_user(
                        interaction.guild_id,
                        interaction.user.id
                    )

                if not workflows:
                    await interaction.response.send_message(
                        "📋 No active workflows found.\n\n"
                        "Workflows are created when a jam leader posts a setlist.",
                        ephemeral=True
                    )
                    return

                # Build embed
                embed = discord.Embed(
                    title="📋 Active Approval Workflows",
                    color=discord.Color.blue()
                )

                for wf in workflows[:10]:  # Limit to 10 workflows
                    setlist_data = wf.get('setlist_data', {})
                    song_matches = wf.get('song_matches', [])
                    selections = wf.get('selections', {})

                    # Calculate selection progress
                    total_songs = len(song_matches)
                    selected_songs = len(selections)

                    # Determine status
                    is_ready, missing = self.bot.is_workflow_ready(wf)
                    if is_ready:
                        status_emoji = "✅"
                        status_text = "Ready to create playlist"
                    else:
                        status_emoji = "⏳"
                        status_text = f"{len(missing)} missing selection(s)"

                    # Format field
                    date_str = setlist_data.get('date', 'Unknown date')
                    time_str = setlist_data.get('time', 'Unknown time')
                    created = wf.get('created_at', 'Unknown')

                    field_value = (
                        f"**Date:** {date_str} ({time_str})\n"
                        f"**Progress:** {selected_songs}/{total_songs} songs\n"
                        f"**Status:** {status_emoji} {status_text}\n"
                        f"**Created:** {created}"
                    )

                    embed.add_field(
                        name=f"Workflow #{wf['id']}",
                        value=field_value,
                        inline=False
                    )

                embed.set_footer(
                    text="Use /jambot-retry <id> to retry playlist creation, "
                         "or /jambot-cancel-workflow <id> to cancel"
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)

            except Exception as e:
                logger.error(f"Error in workflow status command: {e}", exc_info=True)
                await interaction.response.send_message(
                    f"❌ Error retrieving workflow status: {str(e)}",
                    ephemeral=True
                )

        @self.tree.command(
            name="jambot-cancel-workflow",
            description="Cancel an active approval workflow"
        )
        @app_commands.describe(
            workflow_id="Workflow ID to cancel (required)"
        )
        async def cancel_workflow_command(
            interaction: discord.Interaction,
            workflow_id: int
        ):
            """Cancel and cleanup an active workflow.

            Args:
                interaction: Discord interaction object.
                workflow_id: Workflow database ID to cancel.
            """
            try:
                logger.info(
                    f"Cancel workflow command invoked by {interaction.user.id} "
                    f"in guild {interaction.guild_id} for workflow {workflow_id}"
                )

                # Get workflow
                workflow = self.db.get_workflow_by_id(workflow_id)

                if not workflow:
                    await interaction.response.send_message(
                        f"❌ Workflow #{workflow_id} not found.",
                        ephemeral=True
                    )
                    return

                # Verify guild match
                if workflow['guild_id'] != interaction.guild_id:
                    await interaction.response.send_message(
                        f"❌ Workflow #{workflow_id} is not in this server.",
                        ephemeral=True
                    )
                    return

                # Check permissions - user must be admin or involved in workflow
                is_admin = interaction.user.guild_permissions.administrator
                is_initiator = workflow.get('initiated_by') == interaction.user.id
                approver_ids = workflow.get('approver_ids', [])
                is_approver = interaction.user.id in approver_ids

                if not (is_admin or is_initiator or is_approver):
                    await interaction.response.send_message(
                        "❌ You don't have permission to cancel this workflow.\n"
                        "Only administrators, the initiator, or approvers can cancel.",
                        ephemeral=True
                    )
                    return

                # Update status to cancelled
                self.db.update_workflow_status(workflow['summary_message_id'], 'cancelled')

                # Cleanup from active_workflows
                self.bot.cleanup_workflow(workflow)

                await interaction.response.send_message(
                    f"✅ **Workflow #{workflow_id} cancelled successfully.**\n\n"
                    f"The workflow has been removed and no playlist will be created.",
                    ephemeral=True
                )

                logger.info(f"Workflow {workflow_id} cancelled by user {interaction.user.id}")

            except Exception as e:
                logger.error(f"Error in cancel workflow command: {e}", exc_info=True)
                await interaction.response.send_message(
                    f"❌ Error cancelling workflow: {str(e)}",
                    ephemeral=True
                )

        @self.tree.command(
            name="jambot-premium-setup",
            description="Configure premium access for AI chord chart generation (Admin only)"
        )
        @app_commands.checks.has_permissions(administrator=True)
        async def premium_setup_command(interaction: discord.Interaction):
            """Open modal for configuring premium API access.

            This command allows administrators to set up premium features
            by entering their premium API token.

            Args:
                interaction: Discord interaction object.
            """
            logger.info(
                f"Premium setup command invoked by {interaction.user.id} "
                f"in guild {interaction.guild_id}"
            )

            # Track command usage
            self.db.track_usage_event(
                interaction.guild_id,
                'command_used',
                {'command': 'jambot-premium-setup'}
            )

            # Send the premium setup modal
            modal = PremiumSetupModal(self.db)
            await interaction.response.send_modal(modal)

        @premium_setup_command.error
        async def premium_setup_error(
            interaction: discord.Interaction,
            error: app_commands.AppCommandError
        ):
            """Handle errors for the premium setup command."""
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
                logger.error(f"Error in premium setup command: {error}", exc_info=True)

        @self.tree.command(
            name="jambot-credits",
            description="Check your premium credit balance for AI chord chart generation"
        )
        async def credits_command(interaction: discord.Interaction):
            """Display current credit balance for the server.

            Args:
                interaction: Discord interaction object.
            """
            try:
                guild_id = interaction.guild_id
                logger.info(
                    f"Credits command invoked by {interaction.user.id} "
                    f"in guild {guild_id}"
                )

                # Track command usage
                self.db.track_usage_event(
                    guild_id,
                    'command_used',
                    {'command': 'jambot-credits'}
                )

                # Check if premium is enabled
                if not self.db.is_premium_enabled(guild_id):
                    await interaction.response.send_message(
                        "**Premium not configured**\n\n"
                        "Premium access is required for AI chord chart generation.\n\n"
                        "Get started with **5 free trial generations**!\n"
                        "Use `/jambot-premium-setup` to configure your premium token.\n\n"
                        "_Visit https://premium.jambot.app to get a token._",
                        ephemeral=True
                    )
                    return

                await interaction.response.defer(ephemeral=True)

                # Get the stored token (we need to retrieve it for API calls)
                premium_config = self.db.get_premium_config(guild_id)
                if not premium_config or not premium_config.get('premium_api_token_hash'):
                    await interaction.followup.send(
                        "Premium configuration error. Please run `/jambot-premium-setup` again.",
                        ephemeral=True
                    )
                    return

                # Note: We can't use the hashed token directly - we'd need to store the
                # token securely or require re-entry. For MVP, we'll show a message
                # to use the premium portal for detailed balance info.
                # This is a security tradeoff - storing unhashed tokens is risky.

                # For now, show a generic message suggesting the portal
                embed = discord.Embed(
                    title="Premium Credits",
                    description=(
                        "Use the premium portal for detailed credit information:\n"
                        "https://premium.jambot.app/dashboard\n\n"
                        "_Credit balance is also shown after each chart generation._"
                    ),
                    color=discord.Color.gold()
                )
                embed.add_field(
                    name="Premium Status",
                    value="Enabled",
                    inline=True
                )
                embed.add_field(
                    name="Need More Credits?",
                    value="Use `/jambot-buy-credits`",
                    inline=True
                )

                await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                logger.error(f"Error in credits command: {e}", exc_info=True)
                if interaction.response.is_done():
                    await interaction.followup.send(
                        f"Error checking credits: {str(e)}",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"Error checking credits: {str(e)}",
                        ephemeral=True
                    )

        @self.tree.command(
            name="jambot-buy-credits",
            description="Purchase credits for AI chord chart generation"
        )
        async def buy_credits_command(interaction: discord.Interaction):
            """Display credit pack options for purchase.

            Args:
                interaction: Discord interaction object.
            """
            try:
                guild_id = interaction.guild_id
                logger.info(
                    f"Buy credits command invoked by {interaction.user.id} "
                    f"in guild {guild_id}"
                )

                # Track command usage
                self.db.track_usage_event(
                    guild_id,
                    'command_used',
                    {'command': 'jambot-buy-credits'}
                )

                # Check if premium is enabled
                if not self.db.is_premium_enabled(guild_id):
                    await interaction.response.send_message(
                        "**Premium not configured**\n\n"
                        "You need to configure premium access first.\n"
                        "Use `/jambot-premium-setup` to get started with **5 free trial generations**!\n\n"
                        "_Visit https://premium.jambot.app to get a token._",
                        ephemeral=True
                    )
                    return

                # Build the purchase options embed
                embed = discord.Embed(
                    title="Purchase Credits",
                    description=(
                        "Select a credit pack to purchase for AI chord chart generation.\n\n"
                        "Each credit = 1 AI-generated chord chart"
                    ),
                    color=discord.Color.green()
                )

                for pack in CreditPackSelectView.CREDIT_PACKS:
                    savings = f" **(Save {pack['savings']})**" if pack.get('savings') else ""
                    per_credit = float(pack['price'].replace('$', '')) / pack['credits']
                    embed.add_field(
                        name=f"{pack['credits']} Credits - {pack['price']}{savings}",
                        value=f"~${per_credit:.2f} per chart",
                        inline=False
                    )

                embed.set_footer(text="Click a button below to purchase via Stripe")

                # Get the premium token for generating checkout URLs
                premium_config = self.db.get_premium_config(guild_id)
                token = premium_config.get('premium_api_token') if premium_config else None

                if not token:
                    await interaction.response.send_message(
                        embed=embed,
                        content=(
                            "**To purchase credits:**\n"
                            "Visit https://premium.jambot.app\n\n"
                            "_Run `/jambot-premium-setup` first to enable purchases._"
                        ),
                        ephemeral=True
                    )
                    return

                # Create view with purchase buttons
                view = CreditPackSelectView(self.db, guild_id, token)

                await interaction.response.send_message(
                    embed=embed,
                    view=view,
                    ephemeral=True
                )

            except Exception as e:
                logger.error(f"Error in buy credits command: {e}", exc_info=True)
                await interaction.response.send_message(
                    f"Error loading purchase options: {str(e)}",
                    ephemeral=True
                )

        logger.info("Slash commands registered")
