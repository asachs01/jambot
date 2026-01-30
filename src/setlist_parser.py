"""Setlist message parsing for Jambot."""
import re
from typing import Optional, List, Dict, Tuple
from src.logger import logger


class SetlistParser:
    """Parse setlist messages from Discord."""

    # Default regex patterns for setlist detection
    # Note: Handles both straight apostrophe (') and curly quote (') from Discord
    # The (?:\s*\([^)]*\))? allows optional parenthetical comments between "setlist" and "for"
    DEFAULT_INTRO_PATTERN = r"here['\u2019]s\s+the\s+(?:upcoming\s+)?setlist(?:\s*\([^)]*\))?\s+for\s+the\s+(.+?)\s+jam\s+on\s+(.+?)\."

    # Default song line pattern - matches numbered songs with optional key in parentheses
    # Examples: "1. Will the Circle (G)" or "1. Joy to the World"
    # Group 1: song number
    # Group 2: song title
    # Group 3: key (optional, e.g., "G", "Am", "F#")
    # Group 4: extra notes after key (optional)
    DEFAULT_SONG_PATTERN = r'^\s*(\d+)\.\s+(.+?)(?:\s+\(([A-Ga-g][#b]?[mM]?(?:aj|in)?)\)(.*))?$'

    # Compiled default patterns for class-level use
    SETLIST_INTRO_PATTERN = re.compile(DEFAULT_INTRO_PATTERN, re.IGNORECASE)
    SONG_LINE_PATTERN = re.compile(DEFAULT_SONG_PATTERN, re.MULTILINE)

    # Heuristic patterns for detecting potential setlists (used for smart detection)
    # These are looser patterns to catch various setlist formats
    NUMBERED_LIST_PATTERN = re.compile(r'^\s*\d+[.)]\s+.+', re.MULTILINE)
    SETLIST_KEYWORDS = ['setlist', 'set list', 'song list', 'songs for', 'jam on', 'practice']

    def __init__(self, intro_pattern: Optional[str] = None, song_pattern: Optional[str] = None):
        """Initialize setlist parser with optional custom patterns.

        Args:
            intro_pattern: Custom regex pattern for setlist intro line.
                          Must have 2 capture groups: (time) and (date).
            song_pattern: Custom regex pattern for song lines.
                         Must have at least 2 capture groups: (number) and (title).
        """
        # Use custom patterns if provided, otherwise use defaults
        if intro_pattern:
            try:
                self._intro_pattern = re.compile(intro_pattern, re.IGNORECASE)
                logger.info(f"Using custom intro pattern: {intro_pattern}")
            except re.error as e:
                logger.error(f"Invalid intro pattern '{intro_pattern}': {e}, using default")
                self._intro_pattern = self.SETLIST_INTRO_PATTERN
        else:
            self._intro_pattern = self.SETLIST_INTRO_PATTERN

        if song_pattern:
            try:
                self._song_pattern = re.compile(song_pattern, re.MULTILINE)
                logger.info(f"Using custom song pattern: {song_pattern}")
            except re.error as e:
                logger.error(f"Invalid song pattern '{song_pattern}': {e}, using default")
                self._song_pattern = self.SONG_LINE_PATTERN
        else:
            self._song_pattern = self.SONG_LINE_PATTERN

        logger.info("SetlistParser initialized")

    def is_setlist_message(self, content: str) -> bool:
        """Check if a message contains a setlist.

        Args:
            content: Message content to check.

        Returns:
            True if message appears to be a setlist.
        """
        logger.info(f"Checking if message is setlist... (length: {len(content)} chars)")
        logger.info(f"First 100 chars: {repr(content[:100])}")

        match = self._intro_pattern.search(content)
        if match:
            time = match.group(1).strip()
            date = match.group(2).strip()
            logger.info(f"✅ Setlist detected: {time} jam on {date}")
            return True

        logger.debug(f"❌ Not a setlist - pattern didn't match")
        logger.debug(f"Pattern: {self._intro_pattern.pattern}")
        return False

    def parse_setlist(self, content: str) -> Optional[Dict]:
        """Parse a setlist message.

        Args:
            content: Message content containing the setlist.

        Returns:
            Dictionary with 'date', 'time', and 'songs' list, or None if parsing fails.
        """
        try:
            # Debug: Show full message content
            logger.debug(f"Parsing setlist message (length: {len(content)} chars)")
            logger.debug(f"Full message content:\n{content}")

            # Extract time and date from intro
            intro_match = self._intro_pattern.search(content)
            if not intro_match:
                logger.warning("Could not find setlist intro pattern")
                return None

            time = intro_match.group(1).strip()
            date = intro_match.group(2).strip()

            # Extract songs
            songs = []
            logger.debug(f"Looking for songs with pattern: {self._song_pattern.pattern}")
            for match in self._song_pattern.finditer(content):
                # group(1) is the song number, group(2) is the song title
                # group(3) is the optional key, group(4) is optional notes after key
                song_number = int(match.group(1))
                song_title = match.group(2).strip()

                # Remove all trailing keys (anything in parentheses) from the song title
                # This handles cases like "Song Title (A) (faster)" where multiple keys exist
                song_title = re.sub(r'\s*\([^)]+\)\s*$', '', song_title).strip()
                # Keep removing until no more trailing parentheses
                while re.search(r'\s*\([^)]+\)\s*$', song_title):
                    song_title = re.sub(r'\s*\([^)]+\)\s*$', '', song_title).strip()

                logger.debug(f"Found song: {song_number}. {song_title}")
                # key = match.group(3)  # We ignore the key for now

                if song_title:
                    songs.append({
                        'number': song_number,
                        'title': song_title,
                    })

            if not songs:
                logger.warning("No songs found in setlist message")
                logger.debug(f"Song pattern: {self._song_pattern.pattern}")
                # Show a sample of lines from the message
                lines = content.split('\n')
                logger.debug(f"Message has {len(lines)} lines:")
                for i, line in enumerate(lines[:10]):  # Show first 10 lines
                    logger.debug(f"  Line {i}: {repr(line)}")
                return None

            result = {
                'date': date,
                'time': time,
                'songs': songs,
            }

            logger.info(f"Parsed setlist for {time} jam on {date} with {len(songs)} songs")
            return result

        except Exception as e:
            logger.error(f"Error parsing setlist: {e}")
            return None

    def parse_manual_song_command(self, content: str) -> Optional[Dict]:
        """Parse manual song override command.

        Format: @jambot use this version of [song name] for [setlist date] [spotify link]

        Args:
            content: Command message content.

        Returns:
            Dictionary with 'song_title', 'date', and 'spotify_url', or None if invalid.
        """
        try:
            # Pattern for manual command
            # Flexible to allow "use this for..." or "use this version of ... for..."
            pattern = re.compile(
                r'use\s+this(?:\s+version\s+of)?\s+(.+?)\s+for\s+(.+?)\s+(https?://open\.spotify\.com/track/\S+)',
                re.IGNORECASE
            )

            match = pattern.search(content)
            if not match:
                logger.warning("Could not parse manual song command")
                return None

            song_title = match.group(1).strip()
            date = match.group(2).strip()
            spotify_url = match.group(3).strip()

            result = {
                'song_title': song_title,
                'date': date,
                'spotify_url': spotify_url,
            }

            logger.info(f"Parsed manual song command: {song_title} for {date}")
            return result

        except Exception as e:
            logger.error(f"Error parsing manual song command: {e}")
            return None

    @classmethod
    def detect_potential_setlist(cls, content: str) -> Tuple[bool, Dict]:
        """Detect if a message might be a setlist using heuristics.

        This is a looser detection than is_setlist_message(), used for
        scanning channels to find setlist candidates for pattern learning.

        Args:
            content: Message content to check.

        Returns:
            Tuple of (is_potential_setlist, details_dict)
            details_dict contains: 'has_numbered_list', 'numbered_items', 'has_keywords',
                                  'matched_keywords', 'confidence'
        """
        details = {
            'has_numbered_list': False,
            'numbered_items': [],
            'has_keywords': False,
            'matched_keywords': [],
            'confidence': 0.0
        }

        # Check for numbered list items
        numbered_matches = cls.NUMBERED_LIST_PATTERN.findall(content)
        if numbered_matches:
            details['has_numbered_list'] = True
            details['numbered_items'] = [m.strip() for m in numbered_matches[:10]]  # First 10

        # Check for setlist keywords (case-insensitive)
        content_lower = content.lower()
        for keyword in cls.SETLIST_KEYWORDS:
            if keyword in content_lower:
                details['has_keywords'] = True
                details['matched_keywords'].append(keyword)

        # Calculate confidence score
        confidence = 0.0
        if details['has_numbered_list']:
            num_items = len(numbered_matches)
            if num_items >= 5:
                confidence += 0.5
            elif num_items >= 3:
                confidence += 0.3
            else:
                confidence += 0.1

        if details['has_keywords']:
            confidence += 0.3 * len(details['matched_keywords'])

        # Bonus if it has both numbered list AND keywords
        if details['has_numbered_list'] and details['has_keywords']:
            confidence += 0.2

        details['confidence'] = min(confidence, 1.0)

        is_potential = details['confidence'] >= 0.3

        return (is_potential, details)

    @classmethod
    def analyze_setlist_structure(cls, content: str) -> Dict:
        """Analyze a setlist message and extract its structural components.

        This method examines a message and identifies:
        - The intro/header line format
        - The song line format
        - Extracted time and date (if found)
        - List of songs

        Args:
            content: Message content to analyze.

        Returns:
            Dictionary with analysis results including detected structure.
        """
        result = {
            'intro_line': None,
            'detected_time': None,
            'detected_date': None,
            'songs': [],
            'song_format': None,
            'has_keys': False,
            'intro_pattern_suggestion': None,
            'success': False
        }

        lines = content.strip().split('\n')
        if not lines:
            return result

        # Try to find intro line - look for first non-empty line before numbered items
        intro_line = None
        song_start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and re.match(r'^\d+[.)]\s+', stripped):
                song_start_idx = i
                break
            elif stripped:
                intro_line = stripped
                result['intro_line'] = intro_line

        # Try to extract time and date from intro using default pattern
        if intro_line:
            intro_match = cls.SETLIST_INTRO_PATTERN.search(intro_line)
            if intro_match:
                result['detected_time'] = intro_match.group(1).strip()
                result['detected_date'] = intro_match.group(2).strip()
            else:
                # Try to find date-like patterns
                date_patterns = [
                    r'(\d{1,2}/\d{1,2}/\d{2,4})',  # MM/DD/YY or MM/DD/YYYY
                    r'(\d{1,2}-\d{1,2}-\d{2,4})',  # MM-DD-YY or MM-DD-YYYY
                    r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,?\s+\d{4})?)',  # Month DD, YYYY
                ]
                for pattern in date_patterns:
                    date_match = re.search(pattern, intro_line, re.IGNORECASE)
                    if date_match:
                        result['detected_date'] = date_match.group(1)
                        break

                # Try to find time-like patterns
                time_patterns = [
                    r'(\d{1,2}:\d{2}\s*(?:am|pm)?)',  # HH:MM am/pm
                    r'(\d{1,2}\s*(?:am|pm))',  # H am/pm
                ]
                for pattern in time_patterns:
                    time_match = re.search(pattern, intro_line, re.IGNORECASE)
                    if time_match:
                        result['detected_time'] = time_match.group(1)
                        break

        # Parse songs from numbered list
        song_pattern_with_key = re.compile(
            r'^\s*(\d+)[.)]\s+(.+?)\s+\(([A-Ga-g][#b]?[mM]?(?:aj|in)?)\)\s*(.*)$'
        )
        song_pattern_no_key = re.compile(r'^\s*(\d+)[.)]\s+(.+?)\s*$')

        songs_with_keys = 0
        songs_without_keys = 0

        for line in lines[song_start_idx:]:
            stripped = line.strip()
            if not stripped:
                continue

            # Try pattern with key first
            match = song_pattern_with_key.match(stripped)
            if match:
                result['songs'].append({
                    'number': int(match.group(1)),
                    'title': match.group(2).strip(),
                    'key': match.group(3),
                    'notes': match.group(4).strip() if match.group(4) else None
                })
                songs_with_keys += 1
                continue

            # Try pattern without key
            match = song_pattern_no_key.match(stripped)
            if match:
                result['songs'].append({
                    'number': int(match.group(1)),
                    'title': match.group(2).strip(),
                    'key': None,
                    'notes': None
                })
                songs_without_keys += 1

        # Determine if setlist uses keys
        result['has_keys'] = songs_with_keys > songs_without_keys

        if result['songs']:
            result['success'] = True
            if result['has_keys']:
                result['song_format'] = 'numbered_with_key'
            else:
                result['song_format'] = 'numbered_no_key'

        return result

    @classmethod
    def test_pattern_against_message(
        cls,
        content: str,
        intro_pattern: str,
        song_pattern: str
    ) -> Dict:
        """Test custom patterns against a message.

        Args:
            content: Message content to test against.
            intro_pattern: Regex pattern for intro line.
            song_pattern: Regex pattern for song lines.

        Returns:
            Dictionary with test results including matched songs.
        """
        result = {
            'intro_matched': False,
            'intro_groups': None,
            'songs_matched': 0,
            'song_samples': [],
            'errors': []
        }

        # Test intro pattern
        try:
            intro_re = re.compile(intro_pattern, re.IGNORECASE)
            intro_match = intro_re.search(content)
            if intro_match:
                result['intro_matched'] = True
                result['intro_groups'] = intro_match.groups()
        except re.error as e:
            result['errors'].append(f"Invalid intro pattern: {e}")

        # Test song pattern
        try:
            song_re = re.compile(song_pattern, re.MULTILINE)
            song_matches = list(song_re.finditer(content))
            result['songs_matched'] = len(song_matches)
            # Get first 3 as samples
            for match in song_matches[:3]:
                result['song_samples'].append({
                    'full_match': match.group(0).strip(),
                    'groups': match.groups()
                })
        except re.error as e:
            result['errors'].append(f"Invalid song pattern: {e}")

        return result
