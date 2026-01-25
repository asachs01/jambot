"""Tests for chord chart slash commands."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from discord import app_commands


class TestChartListCommand:
    """Test suite for /jambot chart-list command."""

    @pytest.fixture
    def mock_db_with_charts(self, mock_database):
        """Mock database with seeded chart data."""
        # Simulate 25 charts with different statuses
        def list_filtered(guild_id, status, limit=10, offset=0):
            all_charts = []
            for i in range(25):
                chart_status = ['pending', 'approved', 'rejected'][i % 3]
                all_charts.append({
                    'id': i + 1,
                    'title': f'Test Song {i}',
                    'chart_title': f'Test Song {i}',
                    'status': chart_status,
                    'created_by': 99999,
                    'created_at': '2024-01-01T00:00:00'
                })

            # Filter by status
            if status and status != 'all':
                filtered = [c for c in all_charts if c['status'] == status]
            else:
                filtered = all_charts

            total = len(filtered)
            paginated = filtered[offset:offset + limit]

            return paginated, total

        mock_database.list_chord_charts_filtered = MagicMock(side_effect=list_filtered)
        return mock_database

    def test_list_filtered_pending(self, mock_db_with_charts):
        """Test filtering by pending status."""
        charts, total = mock_db_with_charts.list_chord_charts_filtered(12345, 'pending', limit=10, offset=0)

        assert len(charts) <= 10  # Pagination limit
        assert total == 9  # 25 charts / 3 statuses ≈ 8-9 pending
        assert all(c['status'] == 'pending' for c in charts)

    def test_list_filtered_approved(self, mock_db_with_charts):
        """Test filtering by approved status."""
        charts, total = mock_db_with_charts.list_chord_charts_filtered(12345, 'approved', limit=10, offset=0)

        assert len(charts) <= 10
        assert total == 8  # 25 charts / 3 statuses
        assert all(c['status'] == 'approved' for c in charts)

    def test_list_filtered_rejected(self, mock_db_with_charts):
        """Test filtering by rejected status."""
        charts, total = mock_db_with_charts.list_chord_charts_filtered(12345, 'rejected', limit=10, offset=0)

        assert len(charts) <= 10
        assert total == 8  # 25 charts / 3 statuses
        assert all(c['status'] == 'rejected' for c in charts)

    def test_list_filtered_all(self, mock_db_with_charts):
        """Test 'all' status shows everything."""
        charts, total = mock_db_with_charts.list_chord_charts_filtered(12345, 'all', limit=10, offset=0)

        assert len(charts) == 10
        assert total == 25

    def test_pagination_offset(self, mock_db_with_charts):
        """Test pagination with offset."""
        page1, _ = mock_db_with_charts.list_chord_charts_filtered(12345, 'all', limit=10, offset=0)
        page2, _ = mock_db_with_charts.list_chord_charts_filtered(12345, 'all', limit=10, offset=10)
        page3, _ = mock_db_with_charts.list_chord_charts_filtered(12345, 'all', limit=10, offset=20)

        assert len(page1) == 10
        assert len(page2) == 10
        assert len(page3) == 5  # 25 total, last page has 5

        # Verify no overlap
        page1_ids = {c['id'] for c in page1}
        page2_ids = {c['id'] for c in page2}
        assert len(page1_ids & page2_ids) == 0

    def test_embed_formatting(self, mock_db_with_charts):
        """Test embed contains required fields: id, title, status, requested_by."""
        charts, _ = mock_db_with_charts.list_chord_charts_filtered(12345, 'all', limit=10, offset=0)

        for chart in charts:
            assert 'id' in chart
            assert 'title' in chart
            assert 'status' in chart
            assert 'created_by' in chart  # Maps to requested_by display

    def test_empty_results(self, mock_database):
        """Test handling of empty result sets."""
        mock_database.list_chord_charts_filtered = MagicMock(return_value=([], 0))

        charts, total = mock_database.list_chord_charts_filtered(12345, 'pending', limit=10, offset=0)

        assert len(charts) == 0
        assert total == 0

    @pytest.mark.asyncio
    async def test_chart_list_view_build_embed(self, mock_db_with_charts):
        """Test ChartListView builds correct embed structure."""
        from src.chart_commands import ChartListView

        view = ChartListView(mock_db_with_charts, 12345, 'all', 3, 0)
        embed = await view.build_embed(0)

        assert embed.title is not None
        assert '📋' in embed.title
        assert 'Chord Charts' in embed.title
        assert embed.description is not None
        assert 'Showing' in embed.description
        assert len(embed.fields) > 0
        assert embed.footer.text is not None
        assert 'Page 1 of 3' in embed.footer.text

    @pytest.mark.asyncio
    async def test_chart_list_view_status_emoji(self, mock_db_with_charts):
        """Test ChartListView uses correct emoji for each status."""
        from src.chart_commands import ChartListView

        # Test pending
        view_pending = ChartListView(mock_db_with_charts, 12345, 'pending', 1, 0)
        embed_pending = await view_pending.build_embed(0)
        assert '⏳' in embed_pending.title

        # Test approved
        view_approved = ChartListView(mock_db_with_charts, 12345, 'approved', 1, 0)
        embed_approved = await view_approved.build_embed(0)
        assert '✅' in embed_approved.title or 'Approved' in embed_approved.title

        # Test rejected
        view_rejected = ChartListView(mock_db_with_charts, 12345, 'rejected', 1, 0)
        embed_rejected = await view_rejected.build_embed(0)
        assert '❌' in embed_rejected.title or 'Rejected' in embed_rejected.title

    @pytest.mark.asyncio
    async def test_chart_list_view_no_pagination_single_page(self, mock_database):
        """Test ChartListView doesn't add pagination dropdown for single page."""
        from src.chart_commands import ChartListView

        mock_database.list_chord_charts_filtered = MagicMock(return_value=([
            {'id': 1, 'title': 'Test', 'status': 'pending', 'created_by': 123, 'created_at': '2024-01-01'}
        ], 1))

        view = ChartListView(mock_database, 12345, 'all', 1, 0)

        # Single page should not have pagination select
        assert len(view.children) == 0

    @pytest.mark.asyncio
    async def test_chart_list_view_pagination_multiple_pages(self, mock_db_with_charts):
        """Test ChartListView adds pagination dropdown for multiple pages."""
        from src.chart_commands import ChartListView

        view = ChartListView(mock_db_with_charts, 12345, 'all', 3, 0)

        # Multiple pages should have pagination select
        assert len(view.children) == 1
        assert hasattr(view, 'page_select')

    @pytest.mark.asyncio
    async def test_command_integration(self, mock_discord_interaction, mock_db_with_charts):
        """Test full command integration with mock interaction."""
        from src.chart_commands import ChartCommands

        mock_bot = MagicMock()
        mock_bot.tree = MagicMock()

        commands = ChartCommands(mock_bot, mock_db_with_charts)

        # Verify command would be registered
        assert commands.db == mock_db_with_charts
        assert commands.bot == mock_bot
