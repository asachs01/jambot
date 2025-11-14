"""Setlist message parsing for Jambot."""
import re
from typing import Optional, List, Dict
from src.logger import logger


class SetlistParser:
    """Parse setlist messages from Discord."""

    # Regex patterns for setlist detection
    SETLIST_INTRO_PATTERN = re.compile(
        r"here'?s?\s+the\s+(?:upcoming\s+)?setlist\s+for\s+the\s+(.+?)\s+jam\s+on\s+(.+?)\.",
        re.IGNORECASE
    )

    SONG_LINE_PATTERN = re.compile(
        r'^\s*(\d+)\.\s*(.+?)\s*(?:\(([^)]+)\))?\s*$',
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
        return bool(self.SETLIST_INTRO_PATTERN.search(content))

    def parse_setlist(self, content: str) -> Optional[Dict]:
        """Parse a setlist message.

        Args:
            content: Message content containing the setlist.

        Returns:
            Dictionary with 'date', 'time', and 'songs' list, or None if parsing fails.
        """
        try:
            # Extract time and date from intro
            intro_match = self.SETLIST_INTRO_PATTERN.search(content)
            if not intro_match:
                logger.warning("Could not find setlist intro pattern")
                return None

            time = intro_match.group(1).strip()
            date = intro_match.group(2).strip()

            # Extract songs
            songs = []
            for match in self.SONG_LINE_PATTERN.finditer(content):
                song_number = int(match.group(1))
                song_title = match.group(2).strip()
                # key = match.group(3)  # We ignore the key for now

                if song_title:
                    songs.append({
                        'number': song_number,
                        'title': song_title,
                    })

            if not songs:
                logger.warning("No songs found in setlist message")
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
