#!/usr/bin/env python3
"""
Validate TNBGJ songbook import without database connection.

Performs all transformations and validates data structure without actually
inserting into database. Useful for verifying extraction before deployment.
"""

import json
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from import_tnbgj_songbook import (
    transform_song,
    SOURCE_FILE,
    DEFAULT_GUILD_ID,
    SYSTEM_USER_ID
)

def validate_songbook(source_file: str) -> dict:
    """Validate songbook transformations without database.

    Args:
        source_file: Path to extracted JSON file

    Returns:
        Dict with validation results
    """
    print(f"Loading songbook from {source_file}")

    with open(source_file, 'r') as f:
        data = json.load(f)

    songs = data.get('songbook', {}).get('songs', [])
    print(f"Found {len(songs)} songs to validate\n")

    results = {
        'valid': 0,
        'invalid': 0,
        'errors': [],
        'songs': []
    }

    for idx, song in enumerate(songs, 1):
        title = song.get('title', f'Unknown #{idx}')
        try:
            print(f"[{idx}/{len(songs)}] Validating '{title}'")

            # Transform song
            transformed = transform_song(song)

            # Validate required fields
            assert transformed['guild_id'] == DEFAULT_GUILD_ID
            assert transformed['created_by'] == SYSTEM_USER_ID
            assert transformed['title'] == title
            assert 'chart_title' in transformed
            assert 'lyrics' in transformed
            assert 'keys' in transformed
            assert len(transformed['keys']) > 0

            # Validate keys structure
            for key_entry in transformed['keys']:
                assert 'key' in key_entry
                assert 'sections' in key_entry
                for section in key_entry['sections']:
                    assert 'label' in section
                    assert 'rows' in section
                    assert section['rows'] == 8
                    assert 'chords' in section
                    assert isinstance(section['chords'], list)

            # Validate lyrics structure
            has_metadata = False
            for lyric_entry in transformed['lyrics']:
                if '_metadata' in lyric_entry:
                    has_metadata = True
                    assert 'alternate_titles' in lyric_entry['_metadata']
                    assert 'source' in lyric_entry['_metadata']
                    assert 'status' in lyric_entry['_metadata']
                else:
                    assert 'label' in lyric_entry
                    assert 'lines' in lyric_entry

            assert has_metadata, "Missing _metadata in lyrics"

            print(f"  ✓ Valid: {len(transformed['keys'])} key(s), "
                  f"{len([l for l in transformed['lyrics'] if '_metadata' not in l])} lyric section(s)")

            results['valid'] += 1
            results['songs'].append({
                'title': title,
                'keys': [k['key'] for k in transformed['keys']],
                'sections': sum(len(k['sections']) for k in transformed['keys']),
                'total_chords': sum(len(c) for k in transformed['keys'] for s in k['sections'] for c in [s['chords']])
            })

        except Exception as e:
            print(f"  ✗ INVALID: {e}")
            results['invalid'] += 1
            results['errors'].append({'song': title, 'error': str(e)})

    return results


def main():
    """Main entry point."""
    print("=" * 60)
    print("TNBGJ SONGBOOK VALIDATION (DRY RUN)")
    print("=" * 60)
    print()

    # Run validation
    results = validate_songbook(SOURCE_FILE)

    # Print summary
    print()
    print("=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)
    print(f"Valid:   {results['valid']}")
    print(f"Invalid: {results['invalid']}")
    print(f"Total:   {results['valid'] + results['invalid']}")

    if results['errors']:
        print("\nErrors:")
        for error in results['errors']:
            print(f"  - {error['song']}: {error['error']}")

    if results['valid'] > 0:
        print("\nValidated Songs:")
        for song in results['songs']:
            print(f"  • {song['title']}: {song['keys']} "
                  f"({song['sections']} sections, {song['total_chords']} chords)")

    # Exit with error code if any failures
    if results['invalid'] > 0:
        sys.exit(1)

    print(f"\n✓ All {results['valid']} songs validated successfully!")
    print("Ready for database import.")
    sys.exit(0)


if __name__ == '__main__':
    main()
