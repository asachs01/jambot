"""Tests for the SetlistParser class."""
import pytest
from src.setlist_parser import SetlistParser


class TestSetlistParserDetection:
    """Test setlist message detection."""

    def test_detects_standard_setlist(self, sample_setlist_message):
        """Should detect a standard setlist message."""
        parser = SetlistParser()
        assert parser.is_setlist_message(sample_setlist_message) is True

    def test_detects_curly_quote_setlist(self, sample_setlist_message_curly_quotes):
        """Should detect setlist with curly quotes (Discord formatting)."""
        parser = SetlistParser()
        assert parser.is_setlist_message(sample_setlist_message_curly_quotes) is True

    def test_rejects_non_setlist_message(self):
        """Should reject messages that aren't setlists."""
        parser = SetlistParser()
        non_setlist = "Hey everyone, looking forward to the jam tonight!"
        assert parser.is_setlist_message(non_setlist) is False

    def test_rejects_empty_message(self):
        """Should reject empty messages."""
        parser = SetlistParser()
        assert parser.is_setlist_message("") is False

    def test_case_insensitive_detection(self):
        """Should detect setlists regardless of case."""
        parser = SetlistParser()
        message = "HERE'S THE SETLIST FOR THE 3PM JAM ON MARCH 1, 2024.\n1. Test Song"
        assert parser.is_setlist_message(message) is True

    def test_detects_upcoming_setlist(self):
        """Should detect 'upcoming' setlist variation."""
        parser = SetlistParser()
        message = "Here's the upcoming setlist for the evening jam on Friday.\n1. Song One"
        assert parser.is_setlist_message(message) is True

    def test_detects_setlist_with_parenthetical_comment(self):
        """Should detect setlist with parenthetical comment between 'setlist' and 'for'."""
        parser = SetlistParser()
        message = (
            "Here's the upcoming setlist (as requested and dictated by Kristy) "
            "for the 6:30 jam on 02/03/26. If you want to sing any of these, "
            "please let me know.\n\n"
            "1. John Daly (A)\n"
            "2. A hundred years from now (G)"
        )
        assert parser.is_setlist_message(message) is True

        # Also verify parsing extracts correct time and date
        result = parser.parse_setlist(message)
        assert result is not None
        assert result['time'] == '6:30'
        assert result['date'] == '02/03/26'


class TestSetlistParserParsing:
    """Test setlist message parsing."""

    def test_parses_date_and_time(self, sample_setlist_message):
        """Should correctly extract date and time."""
        parser = SetlistParser()
        result = parser.parse_setlist(sample_setlist_message)

        assert result is not None
        assert result['time'] == '7pm'
        assert result['date'] == 'January 15, 2024'

    def test_parses_all_songs(self, sample_setlist_message):
        """Should parse all songs in the setlist."""
        parser = SetlistParser()
        result = parser.parse_setlist(sample_setlist_message)

        assert result is not None
        assert len(result['songs']) == 5
        assert result['songs'][0]['number'] == 1
        assert result['songs'][0]['title'] == 'Will the Circle Be Unbroken'

    def test_parses_songs_without_keys(self, sample_setlist_message_no_keys):
        """Should parse songs that don't have keys specified."""
        parser = SetlistParser()
        result = parser.parse_setlist(sample_setlist_message_no_keys)

        assert result is not None
        assert len(result['songs']) == 3
        assert result['songs'][0]['title'] == 'Amazing Grace'
        assert result['songs'][1]['title'] == "I'll Fly Away"

    def test_strips_key_from_song_title(self, sample_setlist_message):
        """Should strip key notation from song titles."""
        parser = SetlistParser()
        result = parser.parse_setlist(sample_setlist_message)

        # Titles should not include the key in parentheses
        for song in result['songs']:
            assert '(' not in song['title']
            assert ')' not in song['title']

    def test_returns_none_for_invalid_message(self):
        """Should return None for messages that aren't setlists."""
        parser = SetlistParser()
        result = parser.parse_setlist("Just a regular message")
        assert result is None

    def test_parses_various_date_formats(self):
        """Should handle various date formats."""
        parser = SetlistParser()

        messages = [
            "Here's the setlist for the 7pm jam on January 15, 2024.\n1. Song One",
            "Here's the setlist for the morning jam on 1/15/24.\n1. Song One",
            "Here's the setlist for the evening jam on Dec 25.\n1. Song One",
        ]

        for msg in messages:
            result = parser.parse_setlist(msg)
            assert result is not None
            assert len(result['songs']) == 1


class TestSetlistParserCustomPatterns:
    """Test custom pattern support."""

    def test_accepts_custom_intro_pattern(self):
        """Should use custom intro pattern when provided."""
        custom_pattern = r"Songs for tonight's jam on (.+?) at (.+?)\."
        parser = SetlistParser(intro_pattern=custom_pattern)

        message = "Songs for tonight's jam on Friday at 7pm.\n1. Test Song"
        assert parser.is_setlist_message(message) is True

    def test_custom_pattern_extracts_groups(self):
        """Should extract correct groups from custom pattern."""
        custom_pattern = r"Songs for tonight's jam on (.+?) at (.+?)\."
        parser = SetlistParser(intro_pattern=custom_pattern)

        message = "Songs for tonight's jam on Friday at 7pm.\n1. Test Song"
        result = parser.parse_setlist(message)

        assert result is not None
        # Note: Groups are extracted in order, so time and date may be swapped
        assert 'Friday' in [result['time'], result['date']]
        assert '7pm' in [result['time'], result['date']]

    def test_falls_back_to_default_on_invalid_pattern(self, sample_setlist_message):
        """Should use default pattern if custom pattern is invalid."""
        parser = SetlistParser(intro_pattern="[invalid(regex")

        # Should still work with default pattern
        assert parser.is_setlist_message(sample_setlist_message) is True


class TestPotentialSetlistDetection:
    """Test heuristic detection of potential setlists."""

    def test_detects_numbered_list(self):
        """Should detect messages with numbered lists."""
        message = """Practice songs:
1. First Song
2. Second Song
3. Third Song
4. Fourth Song
5. Fifth Song
"""
        is_potential, details = SetlistParser.detect_potential_setlist(message)

        assert is_potential is True
        assert details['has_numbered_list'] is True
        assert len(details['numbered_items']) >= 5

    def test_detects_keywords(self):
        """Should detect setlist-related keywords."""
        message = "Here's the setlist for tomorrow's practice"
        is_potential, details = SetlistParser.detect_potential_setlist(message)

        assert details['has_keywords'] is True
        assert 'setlist' in details['matched_keywords']

    def test_calculates_confidence(self):
        """Should calculate confidence score based on indicators."""
        # High confidence: numbered list + keywords
        message = """Here's the setlist:
1. Song One
2. Song Two
3. Song Three
4. Song Four
5. Song Five
"""
        _, details = SetlistParser.detect_potential_setlist(message)
        assert details['confidence'] >= 0.5

        # Low confidence: just a few numbers
        _, details = SetlistParser.detect_potential_setlist("1. Single item")
        assert details['confidence'] < 0.5


class TestSetlistStructureAnalysis:
    """Test setlist structure analysis."""

    def test_analyzes_structure_with_keys(self, sample_setlist_message):
        """Should analyze setlist with keys in parentheses."""
        result = SetlistParser.analyze_setlist_structure(sample_setlist_message)

        assert result['success'] is True
        assert result['has_keys'] is True
        assert len(result['songs']) == 5
        assert result['songs'][0]['key'] == 'G'

    def test_analyzes_structure_without_keys(self, sample_setlist_message_no_keys):
        """Should analyze setlist without keys."""
        result = SetlistParser.analyze_setlist_structure(sample_setlist_message_no_keys)

        assert result['success'] is True
        assert result['has_keys'] is False

    def test_extracts_intro_line(self, sample_setlist_message):
        """Should extract the intro line."""
        result = SetlistParser.analyze_setlist_structure(sample_setlist_message)

        assert result['intro_line'] is not None
        assert "setlist" in result['intro_line'].lower()

    def test_extracts_date_and_time(self, sample_setlist_message):
        """Should extract date and time from intro."""
        result = SetlistParser.analyze_setlist_structure(sample_setlist_message)

        assert result['detected_time'] == '7pm'
        assert result['detected_date'] == 'January 15, 2024'


class TestPatternTesting:
    """Test pattern testing functionality."""

    def test_pattern_testing_success(self, sample_setlist_message):
        """Should report successful pattern matches."""
        result = SetlistParser.test_pattern_against_message(
            sample_setlist_message,
            SetlistParser.DEFAULT_INTRO_PATTERN,
            SetlistParser.DEFAULT_SONG_PATTERN
        )

        assert result['intro_matched'] is True
        assert result['songs_matched'] >= 5
        assert len(result['errors']) == 0

    def test_pattern_testing_failure(self):
        """Should report pattern match failures."""
        result = SetlistParser.test_pattern_against_message(
            "Not a setlist message",
            SetlistParser.DEFAULT_INTRO_PATTERN,
            SetlistParser.DEFAULT_SONG_PATTERN
        )

        assert result['intro_matched'] is False
        assert result['songs_matched'] == 0

    def test_pattern_testing_invalid_pattern(self, sample_setlist_message):
        """Should report errors for invalid patterns."""
        result = SetlistParser.test_pattern_against_message(
            sample_setlist_message,
            "[invalid(regex",
            SetlistParser.DEFAULT_SONG_PATTERN
        )

        assert len(result['errors']) > 0
        assert "Invalid intro pattern" in result['errors'][0]


class TestManualSongCommand:
    """Test manual song command parsing."""

    def test_parses_manual_command(self):
        """Should parse manual song override command."""
        parser = SetlistParser()
        command = (
            "use this version of Will the Circle Be Unbroken for January 15 "
            "https://open.spotify.com/track/abc123"
        )
        result = parser.parse_manual_song_command(command)

        assert result is not None
        assert result['song_title'] == 'Will the Circle Be Unbroken'
        assert result['date'] == 'January 15'
        assert 'spotify.com/track/abc123' in result['spotify_url']

    def test_parses_alternate_command_format(self):
        """Should parse alternate command format."""
        parser = SetlistParser()
        command = "use this Rocky Top for Friday https://open.spotify.com/track/xyz789"
        result = parser.parse_manual_song_command(command)

        assert result is not None
        assert result['song_title'] == 'Rocky Top'

    def test_returns_none_for_invalid_command(self):
        """Should return None for invalid commands."""
        parser = SetlistParser()
        result = parser.parse_manual_song_command("random message")
        assert result is None
