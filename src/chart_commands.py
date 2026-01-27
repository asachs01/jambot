"""Discord slash commands and mention handler for chord chart management."""
import re
import io
import discord
from discord import app_commands, ui
from typing import Optional, Dict, Any

from src.logger import logger
from src.database import Database
from src.chart_generator import (
    generate_chart_pdf,
    parse_chord_input,
    transpose_key_entry,
    note_to_index,
)
from src.llm_client import LLMClient
from src.premium_client import (
    PremiumClient,
    InvalidTokenError,
    InsufficientCreditsError,
    APIConnectionError,
)


class CreateChartView(ui.View):
    """View with a button to open the chord chart creation modal."""

    def __init__(self, db: Database, prefill_title: str = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.db = db
        self.prefill_title = prefill_title

    @ui.button(label="Create Chart", style=discord.ButtonStyle.primary, emoji="📝")
    async def create_button(self, interaction: discord.Interaction, button: ui.Button):
        guild_id = interaction.guild_id

        # Check if premium is enabled
        is_premium = self.db.is_premium_enabled(guild_id)
        logger.info(f"Premium check for chart creation in guild {guild_id}: enabled={is_premium}")

        if not is_premium:
            await interaction.response.send_message(
                "**Premium Required**\n\n"
                "Creating chord charts requires premium access.\n\n"
                "**Get started with 5 free trial generations!**\n"
                "Use `/jambot-premium-setup` to configure your premium token.\n\n"
                "_Visit https://premium.jambot.io to get a token._",
                ephemeral=True
            )
            return

        modal = ChartCreateModal(self.db, prefill_title=self.prefill_title)
        await interaction.response.send_modal(modal)


class ChartCreateModal(ui.Modal, title="Create Chord Chart"):
    """Modal for inputting chord chart data."""

    def __init__(self, db, prefill_title: str = None):
        super().__init__()
        self.db = db

        # Create TextInputs dynamically to support prefill
        self.song_title = ui.TextInput(
            label="Song Title",
            placeholder="e.g. Mountain Dew",
            max_length=100,
            required=True,
            default=prefill_title or "",
        )
        self.key = ui.TextInput(
            label="Key",
            placeholder="e.g. G",
            max_length=5,
            required=True,
        )
        self.section_labels = ui.TextInput(
            label="Section Labels (comma-separated)",
            placeholder="e.g. Verse,Chorus or A Part,B Part",
            max_length=200,
            required=True,
        )
        self.chords = ui.TextInput(
            label="Chords (sections separated by blank lines)",
            style=discord.TextStyle.paragraph,
            placeholder="G G C G | D D G G\n\nC C G G | D D G G",
            required=True,
        )
        self.lyrics = ui.TextInput(
            label="Lyrics (optional, blank line = section)",
            style=discord.TextStyle.paragraph,
            placeholder="Verse lyrics here...\n\nChorus lyrics here...",
            required=False,
        )

        # Add items to modal
        self.add_item(self.song_title)
        self.add_item(self.key)
        self.add_item(self.section_labels)
        self.add_item(self.chords)
        self.add_item(self.lyrics)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        try:
            chart_data = parse_chord_input(
                title=self.song_title.value,
                key=self.key.value.strip(),
                section_labels=self.section_labels.value,
                chords_text=self.chords.value,
                lyrics_text=self.lyrics.value if self.lyrics.value else None,
            )

            # Store in database
            self.db.create_chord_chart(
                guild_id=interaction.guild_id,
                title=chart_data['title'],
                chart_title=chart_data.get('chart_title'),
                lyrics=chart_data.get('lyrics'),
                keys=chart_data['keys'],
                created_by=interaction.user.id,
            )

            # Generate PDF with draft status
            chart_data['status'] = 'draft'
            pdf_buf = generate_chart_pdf(chart_data)
            filename = f"{chart_data['title'].replace(' ', '_')}.pdf"
            file = discord.File(fp=pdf_buf, filename=filename)

            await interaction.followup.send(
                f"Chord chart for **{chart_data['title']}** (Key of {self.key.value.strip()}) created as **DRAFT**.\n"
                f"Use `/jambot-chart approve` to mark it as approved.",
                file=file,
            )

        except Exception as e:
            logger.error(f"Error creating chord chart: {e}", exc_info=True)
            await interaction.followup.send(
                f"Error creating chart: {e}", ephemeral=True
            )


def _create_chart_preview_embed(chart_data: Dict[str, Any]) -> discord.Embed:
    """Create a Discord embed preview for a chord chart.

    Args:
        chart_data: Chart data dict with title, keys, sections, status.

    Returns:
        Discord Embed with chart preview.
    """
    title = chart_data.get('title', 'Unknown')
    artist = chart_data.get('artist')
    status = chart_data.get('status', 'approved')
    source = chart_data.get('source', 'user_created')

    # Build title string
    embed_title = title
    if artist:
        embed_title += f" by {artist}"

    # Color based on status
    if status == 'approved':
        color = discord.Color.blue()
    elif status == 'draft':
        color = discord.Color.yellow()
    else:
        color = discord.Color.light_grey()

    embed = discord.Embed(title=embed_title, color=color)

    # Add first 2 sections as fields
    keys = chart_data.get('keys', [])
    if keys and len(keys) > 0:
        sections = keys[0].get('sections', [])
        for section in sections[:2]:  # Show first 2 sections
            label = section.get('label', 'Section')
            chords = section.get('chords', [])

            # Format chord grid as column-major layout (4 chords per line)
            chord_lines = []
            for i in range(0, len(chords), 4):
                chord_line = "  ".join(chords[i:i+4])
                chord_lines.append(chord_line)

            chord_block = "```\n" + "\n".join(chord_lines) + "\n```"
            embed.add_field(name=label, value=chord_block, inline=False)

    # Footer with status
    if status == 'approved':
        footer_text = "Status: Approved"
    elif status == 'draft':
        if source == 'ai_generated':
            footer_text = "Status: Draft | Generated by AI"
        else:
            footer_text = "Status: Draft"
    else:
        footer_text = f"Status: {status}"

    embed.set_footer(text=footer_text)

    return embed


class ChartCommands:
    """Discord slash commands for chord chart management."""

    def __init__(self, bot, db, rate_limiter=None):
        self.bot = bot
        self.db = db
        self.tree = bot.tree
        self.llm_client = LLMClient()
        self.rate_limiter = rate_limiter

    async def setup(self):
        """Register chord chart slash commands."""

        @self.tree.command(
            name="jambot-chart",
            description="Chord chart commands (create, view, list, transpose)"
        )
        @app_commands.describe(
            action="Action to perform",
            song_title="Song title (for create/view/transpose - AI generates if provided with create)",
            key="Key for AI generation (e.g., G, A, D)",
            new_key="Target key (for transpose)",
        )
        @app_commands.choices(action=[
            app_commands.Choice(name="create", value="create"),
            app_commands.Choice(name="view", value="view"),
            app_commands.Choice(name="list", value="list"),
            app_commands.Choice(name="transpose", value="transpose"),
            app_commands.Choice(name="generate", value="generate"),
            app_commands.Choice(name="delete", value="delete"),
        ])
        async def jambot_chart(
            interaction: discord.Interaction,
            action: app_commands.Choice[str],
            song_title: Optional[str] = None,
            key: Optional[str] = None,
            new_key: Optional[str] = None,
        ):
            if action.value == "create":
                # If song title provided, use AI generation
                # Otherwise show manual entry modal
                if song_title:
                    await self._handle_generate(interaction, song_title, key)
                else:
                    await self._handle_create(interaction)
            elif action.value == "view":
                await self._handle_view(interaction, song_title, new_key)
            elif action.value == "list":
                await self._handle_list(interaction)
            elif action.value == "transpose":
                await self._handle_transpose(interaction, song_title, new_key)
            elif action.value == "generate":
                await self._handle_generate(interaction, song_title, key)
            elif action.value == "delete":
                await self._handle_delete(interaction, song_title)

        @jambot_chart.error
        async def chart_error(interaction: discord.Interaction, error):
            logger.error(f"Chart command error: {error}", exc_info=True)
            if interaction.response.is_done():
                await interaction.followup.send(
                    f"An error occurred: {error}", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"An error occurred: {error}", ephemeral=True
                )

        @self.tree.command(
            name="jambot-chart-list",
            description="List chord charts with filtering and pagination (Admin only)"
        )
        @app_commands.describe(
            status="Filter by approval status"
        )
        @app_commands.choices(status=[
            app_commands.Choice(name="All", value="all"),
            app_commands.Choice(name="Pending Approval", value="pending"),
            app_commands.Choice(name="Approved", value="approved"),
            app_commands.Choice(name="Rejected", value="rejected"),
        ])
        @app_commands.checks.has_permissions(administrator=True)
        async def jambot_chart_list(
            interaction: discord.Interaction,
            status: app_commands.Choice[str] = None
        ):
            """List chord charts with pagination and filtering."""
            await interaction.response.defer(thinking=True)

            # Default to 'all' if no status specified
            status_value = status.value if status else 'all'

            # Get total count and first page
            charts, total = self.db.list_chord_charts_filtered(
                interaction.guild_id, status_value, limit=10, offset=0
            )

            total_pages = (total + 9) // 10  # Ceiling division

            # Create view with pagination
            view = ChartListView(
                self.db, interaction.guild_id, status_value,
                total_pages, current_page=0
            )

            # Build initial embed
            embed = await view.build_embed(0)

            await interaction.followup.send(embed=embed, view=view)

        @jambot_chart_list.error
        async def chart_list_error(interaction: discord.Interaction, error):
            """Handle command errors."""
            logger.error(f"Chart list command error: {error}", exc_info=True)

            if isinstance(error, app_commands.errors.MissingPermissions):
                await interaction.response.send_message(
                    "❌ You need administrator permissions to use this command.",
                    ephemeral=True
                )
            else:
                msg = f"An error occurred: {error}"
                if interaction.response.is_done():
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)

    async def _handle_create(self, interaction: discord.Interaction):
        """Open the chord chart creation modal.

        Requires premium access to create new chord charts.
        """
        guild_id = interaction.guild_id

        # Check if premium is enabled
        if not self.db.is_premium_enabled(guild_id):
            await interaction.response.send_message(
                "**Premium Required**\n\n"
                "Creating chord charts requires premium access.\n\n"
                "**Get started with 5 free trial generations!**\n"
                "Use `/jambot-premium-setup` to configure your premium token.\n\n"
                "_Visit https://premium.jambot.io to get a token._\n\n"
                "---\n"
                "_Note: Viewing and transposing existing charts is always free._",
                ephemeral=True
            )
            return

        # Premium is enabled, show the create modal
        modal = ChartCreateModal(self.db)
        await interaction.response.send_modal(modal)

    async def _handle_view(
        self, interaction: discord.Interaction,
        song_title: Optional[str], key: Optional[str]
    ):
        """View/generate a chord chart PDF."""
        if not song_title:
            await interaction.response.send_message(
                "Please provide a song title.", ephemeral=True
            )
            return

        # Rate limit check (per-user)
        rate_limit_remaining = -1  # Store remaining count from first check
        if self.rate_limiter:
            identifier = f"user:{interaction.user.id}:chord"
            allowed, rate_limit_remaining = await self.rate_limiter.check_rate_limit(identifier)

            if not allowed:
                ttl = await self.rate_limiter.get_ttl(identifier)
                minutes = ttl // 60
                seconds = ttl % 60
                await interaction.response.send_message(
                    f"⏱️ Rate limit exceeded. You can make 3 chord chart requests per 10 minutes. "
                    f"Please try again in {minutes}m {seconds}s.",
                    ephemeral=True
                )
                return

        await interaction.response.defer(thinking=True)

        chart = self.db.get_chord_chart(interaction.guild_id, song_title)
        if not chart:
            # Try fuzzy match
            charts = self.db.search_chord_charts(interaction.guild_id, song_title)
            if charts:
                chart = charts[0]
            else:
                await interaction.followup.send(
                    f"No chord chart found for \"{song_title}\".", ephemeral=True
                )
                return

        chart_data = {
            'title': chart['title'],
            'chart_title': chart.get('chart_title') or chart['title'],
            'keys': chart['keys'],
            'lyrics': chart.get('lyrics'),
            'status': chart.get('status', 'draft'),
        }

        # Transpose if a different key was requested
        if key and chart_data['keys']:
            source_key = chart_data['keys'][0]['key']
            if key.upper() != source_key.upper():
                transposed = transpose_key_entry(chart_data['keys'][0], key)
                chart_data['keys'] = [transposed]

        pdf_buf = generate_chart_pdf(chart_data)
        display_key = key or chart_data['keys'][0]['key'] if chart_data['keys'] else '?'
        filename = f"{chart['title'].replace(' ', '_')}_{display_key}.pdf"
        file = discord.File(fp=pdf_buf, filename=filename)

        # Build message with rate limit info if available
        status_msg = " **(DRAFT)**" if chart_data['status'] == 'draft' else ""
        message = f"**{chart['title']}** — Key of {display_key}{status_msg}"
        if self.rate_limiter and rate_limit_remaining >= 0:
            message += f" ({rate_limit_remaining} requests remaining in this 10-minute window)"

        await interaction.followup.send(message, file=file)

    async def _handle_list(self, interaction: discord.Interaction):
        """List all chord charts for this guild."""
        await interaction.response.defer(thinking=True)

        charts = self.db.list_chord_charts(interaction.guild_id)
        if not charts:
            await interaction.followup.send("No chord charts saved yet.")
            return

        lines = []
        for chart in charts:
            keys_str = ", ".join(k['key'] for k in chart.get('keys', []))
            creator = f"<@{chart['created_by']}>" if chart.get('created_by') else "Unknown"
            lines.append(f"- **{chart['title']}** (Key of {keys_str}) — by {creator}")

        msg = "**Chord Charts:**\n" + "\n".join(lines)
        # Truncate if too long for Discord
        if len(msg) > 1900:
            msg = msg[:1900] + "\n..."

        await interaction.followup.send(msg)

    async def _handle_transpose(
        self, interaction: discord.Interaction,
        song_title: Optional[str], new_key: Optional[str]
    ):
        """Add a transposed key variant to an existing chart."""
        if not song_title or not new_key:
            await interaction.response.send_message(
                "Please provide both a song title and a target key.",
                ephemeral=True,
            )
            return

        # Rate limit check (per-user)
        rate_limit_remaining = -1  # Store remaining count from first check
        if self.rate_limiter:
            identifier = f"user:{interaction.user.id}:chord"
            allowed, rate_limit_remaining = await self.rate_limiter.check_rate_limit(identifier)

            if not allowed:
                ttl = await self.rate_limiter.get_ttl(identifier)
                minutes = ttl // 60
                seconds = ttl % 60
                await interaction.response.send_message(
                    f"⏱️ Rate limit exceeded. You can make 3 chord chart requests per 10 minutes. "
                    f"Please try again in {minutes}m {seconds}s.",
                    ephemeral=True
                )
                return

        await interaction.response.defer(thinking=True)

        chart = self.db.get_chord_chart(interaction.guild_id, song_title)
        if not chart:
            charts = self.db.search_chord_charts(interaction.guild_id, song_title)
            if charts:
                chart = charts[0]
            else:
                await interaction.followup.send(
                    f"No chord chart found for \"{song_title}\".", ephemeral=True
                )
                return

        # Check if key already exists
        existing_keys = [k['key'] for k in chart.get('keys', [])]
        if new_key in existing_keys:
            await interaction.followup.send(
                f"**{chart['title']}** already has a Key of {new_key} variant.",
                ephemeral=True,
            )
            return

        # Transpose from first key
        if not chart.get('keys'):
            await interaction.followup.send(
                "Chart has no key data to transpose from.", ephemeral=True
            )
            return

        transposed = transpose_key_entry(chart['keys'][0], new_key)
        new_keys = chart['keys'] + [transposed]

        self.db.update_chord_chart_keys(interaction.guild_id, chart['title'], new_keys)

        # Generate PDF with new key
        chart_data = {
            'title': chart['title'],
            'chart_title': chart.get('chart_title') or chart['title'],
            'keys': [transposed],
            'lyrics': chart.get('lyrics'),
            'status': chart.get('status', 'draft'),
        }
        pdf_buf = generate_chart_pdf(chart_data)
        filename = f"{chart['title'].replace(' ', '_')}_{new_key}.pdf"
        file = discord.File(fp=pdf_buf, filename=filename)

        # Build message with rate limit info if available
        message = f"Added Key of {new_key} to **{chart['title']}**."
        if self.rate_limiter and rate_limit_remaining >= 0:
            message += f" ({rate_limit_remaining} requests remaining in this 10-minute window)"

        await interaction.followup.send(message, file=file)

    async def _handle_generate(
        self, interaction: discord.Interaction,
        song_title: Optional[str],
        key: Optional[str] = None
    ):
        """Generate a chord chart using AI via the Premium API.

        Parses format: "Song Title" or "Song Title by Artist Name"
        """
        guild_id = interaction.guild_id

        if not song_title:
            await interaction.response.send_message(
                "Please provide a song title.\n"
                "Example: `/jambot-chart create Mountain Dew key:G`",
                ephemeral=True
            )
            return

        # Check if premium is enabled
        if not self.db.is_premium_enabled(guild_id):
            await interaction.response.send_message(
                "**Premium Required**\n\n"
                "AI chord chart generation requires premium access.\n\n"
                "**Get started with 5 free trial generations!**\n"
                "Use `/jambot-premium-setup` to configure your premium token.\n\n"
                "_Visit https://premium.jambot.io to get a token._",
                ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        # Parse artist from "by Artist" pattern
        artist = None
        match = re.match(r'^(.+?)\s+by\s+(.+)$', song_title, re.IGNORECASE)
        if match:
            song_title = match.group(1).strip()
            artist = match.group(2).strip()

        # Check if chart already exists with fuzzy search
        existing_chart = self.db.fuzzy_search_chord_chart(guild_id, song_title)

        if existing_chart:
            status = existing_chart.get('status', 'approved')
            if status == 'approved':
                # Return existing chart as PDF
                chart_data = {
                    'title': existing_chart['title'],
                    'keys': existing_chart['keys'],
                    'lyrics': existing_chart.get('lyrics'),
                    'status': status,
                }
                pdf_buf = generate_chart_pdf(chart_data)
                filename = f"{existing_chart['title'].replace(' ', '_')}.pdf"
                file = discord.File(fp=pdf_buf, filename=filename)

                await interaction.followup.send(
                    f"Found existing chart for **{existing_chart['title']}**:",
                    file=file
                )
                return
            else:
                await interaction.followup.send(
                    f"Chart for **{existing_chart['title']}** exists but is pending approval (status: {status})."
                )
                return

        # Get premium token
        premium_config = self.db.get_premium_config(guild_id)
        token = premium_config.get('premium_api_token')

        # Generate via Premium API
        try:
            logger.info(f"Generating chord chart via Premium API: title='{song_title}', artist='{artist}', guild={guild_id}")

            async with PremiumClient() as client:
                result = await client.generate_chart(
                    token=token,
                    guild_id=guild_id,
                    title=song_title,
                    artist=artist,
                    key=key
                )

            if not result.success:
                if result.error == "insufficient_credits":
                    await interaction.followup.send(
                        "**No Credits Remaining**\n\n"
                        f"You have {result.credits_remaining} credits left.\n\n"
                        "Use `/jambot-buy-credits` to purchase more credits.",
                        ephemeral=True
                    )
                    return
                else:
                    await interaction.followup.send(
                        f"Chart generation failed: {result.error}",
                        ephemeral=True
                    )
                    return

            # Extract chart data from API response
            chart = result.chart
            chart_title = chart.get('title', song_title)
            chart_key = chart.get('key', 'G')
            raw_sections = chart.get('sections', [])
            lyrics_data = chart.get('lyrics')

            # Parse sections - API returns chords as pipe-separated strings
            # like "A | A | E7 | E7" but PDF generator expects flat list ["A", "A", "E7", "E7"]
            sections = []
            for section in raw_sections:
                parsed_chords = []
                for chord_line in section.get('chords', []):
                    # Split on pipe and clean up whitespace
                    chords = [c.strip() for c in chord_line.split('|') if c.strip()]
                    parsed_chords.extend(chords)
                sections.append({
                    'label': section.get('label', ''),
                    'chords': parsed_chords,
                })

            # Build keys structure
            keys = [{
                'key': chart_key,
                'sections': sections,
            }]

            # Build lyrics structure if present (must be list of dicts, not string)
            lyrics = None
            if lyrics_data and isinstance(lyrics_data, list):
                lyrics = lyrics_data
            # If AI returned a string for lyrics, ignore it (PDF expects list format)

            # Save to database as draft
            chart_id = self.db.create_chord_chart(
                guild_id=guild_id,
                title=chart_title,
                chart_title=None,
                lyrics=lyrics,
                keys=keys,
                created_by=interaction.user.id,
                source='ai_generated',
                status='draft',
                alternate_titles=None,
            )

            # Save generation history
            self.db.create_generation_history(
                chart_id=chart_id,
                prompt=f"Generate chord chart for '{song_title}'" + (f" by {artist}" if artist else ""),
                response=chart,
                model='premium_api',
            )

            # Generate PDF via API (uses correct TNBGJ format)
            # Build chart data in API format
            api_chart_data = {
                'title': chart_title,
                'key': chart_key,
                'sections': [{'label': s['label'], 'chords': s['chords']} for s in sections],
                'lyrics': lyrics,
            }

            try:
                pdf_bytes = await client.render_pdf(token, api_chart_data)
                pdf_buf = io.BytesIO(pdf_bytes)
            except Exception as pdf_error:
                logger.warning(f"API PDF render failed, falling back to local: {pdf_error}")
                # Fallback to local PDF generation if API fails
                local_chart_data = {
                    'title': chart_title,
                    'keys': keys,
                    'lyrics': lyrics,
                    'status': 'draft',
                }
                pdf_buf = generate_chart_pdf(local_chart_data)

            filename = f"{chart_title.replace(' ', '_')}.pdf"
            file = discord.File(fp=pdf_buf, filename=filename)

            credits_msg = f"({result.credits_remaining} credits remaining)"

            await interaction.followup.send(
                f"Generated chord chart for **{chart_title}** (Key of {chart_key}) - saved as **DRAFT**\n"
                f"{credits_msg}\n\n"
                f"_Use `/jambot-chart approve {chart_title}` to finalize._",
                file=file
            )

        except InvalidTokenError:
            logger.error(f"Invalid premium token for guild {guild_id}")
            await interaction.followup.send(
                "**Invalid Premium Token**\n\n"
                "Your premium token appears to be invalid or expired.\n"
                "Please run `/jambot-premium-setup` again with a valid token.",
                ephemeral=True
            )
        except APIConnectionError as e:
            logger.error(f"Premium API connection error: {e}")
            await interaction.followup.send(
                "**Service Unavailable**\n\n"
                "Unable to connect to the premium API. Please try again later.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Chart generation failed: {e}", exc_info=True)
            await interaction.followup.send(
                "Chart generation failed. Please try again later.",
                ephemeral=True
            )

    async def _handle_delete(
        self, interaction: discord.Interaction,
        song_title: Optional[str]
    ):
        """Delete a chord chart (admin only)."""
        if not song_title:
            await interaction.response.send_message(
                "Please provide a song title to delete.",
                ephemeral=True
            )
            return

        # Check for admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Only administrators can delete chord charts.",
                ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        # Try to find the chart (exact or fuzzy match)
        chart = self.db.get_chord_chart(interaction.guild_id, song_title)
        if not chart:
            charts = self.db.search_chord_charts(interaction.guild_id, song_title)
            if charts:
                chart = charts[0]

        if not chart:
            await interaction.followup.send(
                f"No chord chart found matching \"{song_title}\".",
                ephemeral=True
            )
            return

        # Delete the chart
        try:
            deleted = self.db.delete_chord_chart(interaction.guild_id, chart['title'])

            if deleted:
                await interaction.followup.send(
                    f"Deleted chord chart **{chart['title']}**."
                )
            else:
                await interaction.followup.send(
                    f"Could not find chart \"{chart['title']}\" to delete.",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error deleting chart '{chart['title']}': {e}", exc_info=True)
            await interaction.followup.send(
                f"Unable to delete **{chart['title']}**. Please try again or contact support.",
                ephemeral=True
            )

    async def handle_mention(self, message: discord.Message):
        """Handle @mentions requesting chord charts.

        Patterns recognized:
        - "chord chart for <title> in <key>"
        - "chords for <title>"
        - "chart for <title>"
        - "I need a chord chart for <title> in <key>"
        - "create a chord chart for <title>"
        - "add a chord chart for <title>"
        """
        content = message.content
        # Strip user and role mentions
        content = re.sub(r'<@[!&]?\d+>', '', content).strip()

        # Check for explicit create requests first
        create_patterns = [
            r'(?:create|add|make|new)\s+(?:a\s+)?(?:chord\s*chart|chords?|chart)\s+(?:for\s+)?(.+?)\s+in\s+([A-Ga-g][#b]?)\s*$',
            r'(?:create|add|make|new)\s+(?:a\s+)?(?:chord\s*chart|chords?|chart)\s+(?:for\s+)?(.+?)\s*$',
            r'(?:create|add|make|new)\s+(?:a\s+)?(?:chord\s*chart|chords?|chart)\s*$',
        ]

        is_create_request = False
        song_title = None
        requested_key = None

        for pattern in create_patterns:
            m = re.search(pattern, content, re.IGNORECASE)
            if m:
                is_create_request = True
                if m.lastindex >= 1:
                    song_title = m.group(1).strip().strip('"\'')
                if m.lastindex >= 2:
                    requested_key = m.group(2).strip()
                break

        if is_create_request:
            logger.info(f"Chart create request via mention: title='{song_title}'")

            # Check premium status for create requests
            if not self.db.is_premium_enabled(guild_id):
                await message.reply(
                    "**Premium Required**\n\n"
                    "Creating chord charts requires premium access.\n\n"
                    "**Get started with 5 free trial generations!**\n"
                    "Use `/jambot-premium-setup` to configure your premium token.\n\n"
                    "_Visit https://premium.jambot.io to get a token._"
                )
                return

            view = CreateChartView(self.db, prefill_title=song_title)
            await message.reply(
                "Click below to create a new chord chart:",
                view=view,
            )
            return

        # Try to extract song title for lookup
        lookup_patterns = [
            r'(?:chord\s*chart|chords?|chart)\s+for\s+(.+?)\s+in\s+([A-Ga-g][#b]?)\s*$',
            r'(?:chord\s*chart|chords?|chart)\s+for\s+(.+?)\s*$',
            r'(?:need|want|get)\s+(?:a\s+)?(?:chord\s*chart|chords?|chart)\s+for\s+(.+?)\s+in\s+([A-Ga-g][#b]?)\s*$',
            r'(?:need|want|get)\s+(?:a\s+)?(?:chord\s*chart|chords?|chart)\s+for\s+(.+?)\s*$',
        ]

        for pattern in lookup_patterns:
            m = re.search(pattern, content, re.IGNORECASE)
            if m:
                song_title = m.group(1).strip().strip('"\'')
                if m.lastindex >= 2:
                    requested_key = m.group(2).strip()
                break

        if not song_title:
            return  # Not a chart request

        logger.info(f"Chart mention request: title='{song_title}', key={requested_key}")

        # Rate limit check (per-user) for chart lookups only (not create requests)
        rate_limit_remaining = -1  # Store remaining count from first check
        if not is_create_request and self.rate_limiter:
            identifier = f"user:{message.author.id}:chord"
            allowed, rate_limit_remaining = await self.rate_limiter.check_rate_limit(identifier)

            if not allowed:
                ttl = await self.rate_limiter.get_ttl(identifier)
                minutes = ttl // 60
                seconds = ttl % 60
                await message.reply(
                    f"⏱️ Rate limit exceeded. You can make 3 chord chart requests per 10 minutes. "
                    f"Please try again in {minutes}m {seconds}s."
                )
                return

        guild_id = message.guild.id if message.guild else 0

        # Look up chart
        chart = self.db.get_chord_chart(guild_id, song_title)
        if not chart:
            charts = self.db.search_chord_charts(guild_id, song_title)
            if charts:
                chart = charts[0]

        if chart:
            chart_data = {
                'title': chart['title'],
                'chart_title': chart.get('chart_title') or chart['title'],
                'keys': chart['keys'],
                'lyrics': chart.get('lyrics'),
            }

            # Transpose if needed
            display_key = chart_data['keys'][0]['key'] if chart_data['keys'] else '?'
            if requested_key and chart_data['keys']:
                source_key = chart_data['keys'][0]['key']
                if requested_key.upper() != source_key.upper():
                    transposed = transpose_key_entry(chart_data['keys'][0], requested_key)
                    chart_data['keys'] = [transposed]
                    display_key = requested_key

            pdf_buf = generate_chart_pdf(chart_data)
            filename = f"{chart['title'].replace(' ', '_')}_{display_key}.pdf"
            file = discord.File(fp=pdf_buf, filename=filename)

            # Build message with rate limit info if available
            reply_msg = f"**{chart['title']}** — Key of {display_key}"
            if self.rate_limiter and rate_limit_remaining >= 0:
                reply_msg += f" ({rate_limit_remaining} requests remaining in this 10-minute window)"

            await message.reply(reply_msg, file=file)
        else:
            # Check premium status before offering to create
            if self.db.is_premium_enabled(guild_id):
                view = CreateChartView(self.db, prefill_title=song_title)
                await message.reply(
                    f"I don't have a chord chart for \"{song_title}\" yet. "
                    f"Click below to create one:",
                    view=view,
                )
            else:
                await message.reply(
                    f"I don't have a chord chart for \"{song_title}\" yet.\n\n"
                    f"Creating charts requires premium access. "
                    f"Use `/jambot-premium-setup` to get started with 5 free trial generations!"
                )
