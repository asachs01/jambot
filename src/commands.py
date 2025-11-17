"""Slash commands for Jambot configuration."""
import discord
from discord import app_commands
from discord.ui import Modal, TextInput
from typing import List
from src.logger import logger
from src.database import Database


class ConfigurationModal(Modal, title="Configure Jambot"):
    """Modal for configuring jam leaders and approvers.

    Note: Discord modals don't support user select components directly.
    Users will need to input user IDs. We'll provide a helper command
    to get user IDs easily.
    """

    jam_leaders = TextInput(
        label="Jam Leader User IDs",
        placeholder="Enter user IDs separated by commas (e.g., 123456789, 987654321)",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    approvers = TextInput(
        label="Song Approver User IDs",
        placeholder="Enter user IDs separated by commas (e.g., 123456789, 987654321)",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

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

            # Store configuration in database
            guild_id = interaction.guild_id
            self.db.save_bot_configuration(
                guild_id=guild_id,
                jam_leader_ids=jam_leader_ids,
                approver_ids=approver_ids,
                channel_id=channel_id_value,
                playlist_name_template=playlist_template,
                updated_by=interaction.user.id
            )

            logger.info(
                f"Configuration updated by {interaction.user.id} for guild {guild_id}: "
                f"jam_leaders={jam_leader_ids}, approvers={approver_ids}, "
                f"channel={channel_id_value}, template={playlist_template}"
            )

            # Build confirmation message
            jam_leaders_mentions = ", ".join([f"<@{uid}>" for uid in jam_leader_ids])
            approvers_mentions = ", ".join([f"<@{uid}>" for uid in approver_ids])

            confirm_msg = (
                f"✅ **Configuration updated successfully!**\n\n"
                f"**Jam Leaders:** {jam_leaders_mentions}\n"
                f"**Song Approvers:** {approvers_mentions}"
            )

            if channel_id_value:
                confirm_msg += f"\n**Playlist Channel:** <#{channel_id_value}>"

            if playlist_template:
                confirm_msg += f"\n**Playlist Name:** {playlist_template}"

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

        logger.info("Slash commands registered")
