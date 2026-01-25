"""Discord slash commands and mention handler for chord chart management."""
import re
import io
import discord
from discord import app_commands, ui
from typing import Optional

from src.logger import logger
from src.chart_generator import (
    generate_chart_pdf,
    parse_chord_input,
    transpose_key_entry,
    note_to_index,
)


class CreateChartView(ui.View):
    """View with a button to open the chord chart creation modal."""

    def __init__(self, db, prefill_title: str = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.db = db
        self.prefill_title = prefill_title

    @ui.button(label="Create Chart", style=discord.ButtonStyle.primary, emoji="📝")
    async def create_button(self, interaction: discord.Interaction, button: ui.Button):
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
            label="Lyrics (optional, sections separated by blank lines)",
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


class ChartCommands:
    """Discord slash commands for chord chart management."""

    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.tree = bot.tree

    async def setup(self):
        """Register chord chart slash commands."""

        @self.tree.command(
            name="jambot-chart",
            description="Chord chart commands (create, view, list, transpose)"
        )
        @app_commands.describe(
            action="Action to perform",
            song_title="Song title (for view/transpose)",
            new_key="Target key (for transpose)",
        )
        @app_commands.choices(action=[
            app_commands.Choice(name="create", value="create"),
            app_commands.Choice(name="view", value="view"),
            app_commands.Choice(name="list", value="list"),
            app_commands.Choice(name="transpose", value="transpose"),
            app_commands.Choice(name="approve", value="approve"),
        ])
        async def jambot_chart(
            interaction: discord.Interaction,
            action: app_commands.Choice[str],
            song_title: Optional[str] = None,
            new_key: Optional[str] = None,
        ):
            if action.value == "create":
                await self._handle_create(interaction)
            elif action.value == "view":
                await self._handle_view(interaction, song_title, new_key)
            elif action.value == "list":
                await self._handle_list(interaction)
            elif action.value == "transpose":
                await self._handle_transpose(interaction, song_title, new_key)
            elif action.value == "approve":
                await self._handle_approve(interaction, song_title)

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

    async def _handle_create(self, interaction: discord.Interaction):
        """Open the chord chart creation modal."""
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

        status_msg = " **(DRAFT)**" if chart_data['status'] == 'draft' else ""
        await interaction.followup.send(
            f"**{chart['title']}** — Key of {display_key}{status_msg}",
            file=file,
        )

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

        await interaction.followup.send(
            f"Added Key of {new_key} to **{chart['title']}**.",
            file=file,
        )

    async def _handle_approve(
        self, interaction: discord.Interaction, song_title: Optional[str]
    ):
        """Approve a draft chord chart."""
        if not song_title:
            await interaction.response.send_message(
                "Please provide a song title to approve.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        # Check if user is an approver
        config = self.db.get_bot_configuration(interaction.guild_id)
        approver_ids = config.get('approver_ids', []) if config else []
        if interaction.user.id not in approver_ids:
            await interaction.followup.send(
                "You do not have permission to approve chord charts.", ephemeral=True
            )
            return

        # Get chart
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

        # Check if already approved
        if chart.get('status') == 'approved':
            await interaction.followup.send(
                f"**{chart['title']}** is already approved.", ephemeral=True
            )
            return

        # Approve the chart
        self.db.update_chord_chart_status(
            interaction.guild_id, chart['title'], 'approved', interaction.user.id
        )

        # Generate approved PDF
        chart_data = {
            'title': chart['title'],
            'chart_title': chart.get('chart_title') or chart['title'],
            'keys': chart['keys'],
            'lyrics': chart.get('lyrics'),
            'status': 'approved',
        }
        pdf_buf = generate_chart_pdf(chart_data)
        filename = f"{chart['title'].replace(' ', '_')}.pdf"
        file = discord.File(fp=pdf_buf, filename=filename)

        await interaction.followup.send(
            f"**{chart['title']}** has been approved by <@{interaction.user.id}>.",
            file=file,
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

            await message.reply(
                f"**{chart['title']}** — Key of {display_key}",
                file=file,
            )
        else:
            view = CreateChartView(self.db, prefill_title=song_title)
            await message.reply(
                f"I don't have a chord chart for \"{song_title}\" yet. "
                f"Click below to create one:",
                view=view,
            )
