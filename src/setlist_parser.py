"""Setlist message parsing for Jambot."""
import re
from typing import Optional, List, Dict
from src.logger import logger


class SetlistParser:
    """Parse setlist messages from Discord."""

    # Regex patterns for setlist detection
    # Note: Handles both straight apostrophe (') and curly quote (') from Discord
    SETLIST_INTRO_PATTERN = re.compile(
        r"here['\u2019]s\s+the\s+(?:upcoming\s+)?setlist\s+for\s+the\s+(.+?)\s+jam\s+on\s+(.+?)\.",
        re.IGNORECASE
    )

    # Pattern matches songs with optional number, song name, and key in parentheses
    # Examples: "1. Will the Circle (G)" or "Will the Circle (G)"
    # Also handles optional notes after the key: "Little Maggie (A) faster"
    # Key pattern matches musical keys: A-G with optional #/b and m/M/maj/min modifiers
    SONG_LINE_PATTERN = re.compile(
        r'^\s*(?:(\d+)\.\s+)?(.+?)\s+\(([A-Ga-g][#b]?[mM]?(?:aj|in)?)\)(.*)$',
        re.MULTILINE
    )

    def __init__(self):
        """Initialize setlist parser."""
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

        match = self.SETLIST_INTRO_PATTERN.search(content)
        if match:
            time = match.group(1).strip()
            date = match.group(2).strip()
            logger.info(f"✅ Setlist detected: {time} jam on {date}")
            return True

        logger.debug(f"❌ Not a setlist - pattern didn't match")
        logger.debug(f"Pattern: {self.SETLIST_INTRO_PATTERN.pattern}")
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
            intro_match = self.SETLIST_INTRO_PATTERN.search(content)
            if not intro_match:
                logger.warning("Could not find setlist intro pattern")
                return None

            time = intro_match.group(1).strip()
            date = intro_match.group(2).strip()

            # Extract songs
            songs = []
            song_counter = 1  # For unnumbered songs
            logger.debug(f"Looking for songs with pattern: {self.SONG_LINE_PATTERN.pattern}")
            for match in self.SONG_LINE_PATTERN.finditer(content):
                # group(1) is the optional number, group(2) is the song title, group(3) is the key
                number_str = match.group(1)
                song_number = int(number_str) if number_str else song_counter
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
                    if not number_str:  # Increment counter only for unnumbered songs
                        song_counter += 1

            if not songs:
                logger.warning("No songs found in setlist message")
                logger.debug(f"Song pattern: {self.SONG_LINE_PATTERN.pattern}")
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
