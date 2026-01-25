#!/usr/bin/env python3
"""
Import TNBGJ songbook from extracted JSON to chord_charts database.

Transforms the extracted songbook JSON structure to match the database schema:
- Flattens chord progressions from columns/measures to flat chords array
- Renames lyrics 'section' to 'label'
- Embeds metadata (alternate_titles, artist, source, status) in lyrics JSONB
- Creates separate keys entries for multi-key songs
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import Database

# Configuration constants
DEFAULT_GUILD_ID = 0  # Universal import for all guilds
SYSTEM_USER_ID = 0    # System-generated charts
SOURCE_FILE = "/Users/asachs/Documents/projects/jambot/tnbgj_songbook_extracted.json"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def transform_lyrics(source_lyrics: List[Dict[str, Any]], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Transform lyrics structure and embed metadata.

    Args:
        source_lyrics: Original lyrics with 'section' field
        metadata: Metadata dict (alternate_titles, artist, source, status)

    Returns:
        Transformed lyrics with 'label' field and embedded _metadata
    """
    transformed = []
    for lyric_section in source_lyrics:
        transformed.append({
            'label': lyric_section['section'],  # Rename section -> label
            'lines': lyric_section['lines']
        })

    # Add metadata as special field
    transformed.append({
        '_metadata': metadata
    })

    return transformed


def flatten_chord_progression(
    chord_progression: List[Dict[str, Any]],
    song_keys: List[str]
) -> List[Dict[str, Any]]:
    """Flatten chord progression from columns/measures to flat chords array.

    Args:
        chord_progression: List of progression sections with columns/measures
        song_keys: List of keys from song metadata (e.g. ["D"], ["G", "A"])

    Returns:
        List of key entries matching database schema
    """
    keys_output = []

    # Check if progressions have explicit 'key' fields
    progressions_with_keys = [p for p in chord_progression if 'key' in p]

    if progressions_with_keys:
        # Group progressions by key
        key_groups: Dict[str, List[Dict[str, Any]]] = {}
        for prog in chord_progression:
            if 'key' not in prog:
                # No key specified, skip or warn
                logger.warning(f"Progression section '{prog.get('section', 'unknown')}' has no key field")
                continue

            key = prog['key']
            if key not in key_groups:
                key_groups[key] = []
            key_groups[key].append(prog)

        # Transform each key group
        for key, progs in key_groups.items():
            sections = []
            for prog in progs:
                section = transform_progression_section(prog)
                sections.append(section)

            keys_output.append({
                'key': key,
                'sections': sections
            })
    else:
        # No explicit keys in progressions, create one entry per song key
        for key in song_keys:
            sections = []
            for prog in chord_progression:
                section = transform_progression_section(prog)
                sections.append(section)

            keys_output.append({
                'key': key,
                'sections': sections
            })

    return keys_output


def transform_progression_section(prog: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a single progression section to database format.

    Args:
        prog: Progression section with columns/measures structure

    Returns:
        Section dict with flat chords array
    """
    # Flatten columns/measures into single chords array (column-major order)
    chords = []
    for column in prog.get('columns', []):
        measures = column.get('measures', [])
        chords.extend(measures)

    return {
        'label': prog.get('section', 'Unknown'),
        'rows': 8,  # Standard grid height from chart_generator.py:146
        'endings': None,
        'chords': chords
    }


def transform_song(song: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a song from source JSON to database schema.

    Args:
        song: Source song dict

    Returns:
        Transformed song dict ready for database insertion
    """
    # Validate required fields
    if not song.get('title'):
        raise ValueError("Song missing required 'title' field")
    if not song.get('keys'):
        raise ValueError(f"Song '{song['title']}' missing required 'keys' field")
    if not song.get('chord_progression'):
        raise ValueError(f"Song '{song['title']}' missing required 'chord_progression' field")

    # Create metadata for JSONB embedding
    metadata = {
        'alternate_titles': song.get('alternate_titles', []),
        'artist': song.get('artist'),
        'source': song.get('source', 'imported'),
        'status': song.get('status', 'approved')
    }

    # Transform lyrics
    transformed_lyrics = transform_lyrics(
        song.get('lyrics', []),
        metadata
    )

    # Transform chord progression
    transformed_keys = flatten_chord_progression(
        song['chord_progression'],
        song['keys']
    )

    # Create chart_title (abbreviated if >20 chars)
    title = song['title']
    chart_title = title if len(title) <= 20 else title[:17] + '...'

    return {
        'guild_id': DEFAULT_GUILD_ID,
        'title': title,
        'chart_title': chart_title,
        'lyrics': transformed_lyrics,
        'keys': transformed_keys,
        'created_by': SYSTEM_USER_ID
    }


def import_songbook(source_file: str, db: Database) -> Dict[str, Any]:
    """Import songbook from JSON file to database.

    Args:
        source_file: Path to extracted JSON file
        db: Database instance

    Returns:
        Dict with success/failure/skipped counts and details
    """
    logger.info(f"Loading songbook from {source_file}")

    with open(source_file, 'r') as f:
        data = json.load(f)

    songs = data.get('songbook', {}).get('songs', [])
    logger.info(f"Found {len(songs)} songs to import")

    results = {
        'succeeded': 0,
        'failed': 0,
        'skipped': 0,
        'errors': []
    }

    for idx, song in enumerate(songs, 1):
        title = song.get('title', f'Unknown #{idx}')
        try:
            logger.info(f"[{idx}/{len(songs)}] Processing '{title}'")

            # Transform song to database format
            transformed = transform_song(song)

            # Insert into database
            chart_id = db.create_chord_chart(
                guild_id=transformed['guild_id'],
                title=transformed['title'],
                chart_title=transformed['chart_title'],
                lyrics=transformed['lyrics'],
                keys=transformed['keys'],
                created_by=transformed['created_by']
            )

            logger.info(f"✓ '{title}' imported successfully (chart_id={chart_id})")
            results['succeeded'] += 1

        except ValueError as e:
            logger.error(f"✗ '{title}' validation error: {e}")
            results['skipped'] += 1
            results['errors'].append({'song': title, 'error': str(e)})

        except Exception as e:
            logger.error(f"✗ '{title}' failed: {e}")
            results['failed'] += 1
            results['errors'].append({'song': title, 'error': str(e)})

    return results


def main():
    """Main entry point."""
    logger.info("Starting TNBGJ songbook import")

    # Initialize database
    db = Database()

    # Run import
    results = import_songbook(SOURCE_FILE, db)

    # Print summary
    logger.info("=" * 60)
    logger.info("IMPORT COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Succeeded: {results['succeeded']}")
    logger.info(f"Failed:    {results['failed']}")
    logger.info(f"Skipped:   {results['skipped']}")
    logger.info(f"Total:     {results['succeeded'] + results['failed'] + results['skipped']}")

    if results['errors']:
        logger.info("\nErrors:")
        for error in results['errors']:
            logger.info(f"  - {error['song']}: {error['error']}")

    # Exit with error code if any failures
    if results['failed'] > 0:
        sys.exit(1)

    logger.info("\n✓ All songs imported successfully!")
    sys.exit(0)


if __name__ == '__main__':
    main()
