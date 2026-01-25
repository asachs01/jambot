#!/usr/bin/env python3
"""
Standalone validation for TNBGJ songbook import.

Performs all transformations and validates data structure without requiring
database connection or other dependencies. Copy-pasted transformation logic
for standalone execution.
"""

import json
import sys
from typing import Dict, List, Any

# Configuration constants
DEFAULT_GUILD_ID = 0
SYSTEM_USER_ID = 0
SOURCE_FILE = "/Users/asachs/Documents/projects/jambot/tnbgj_songbook_extracted.json"


def transform_lyrics(source_lyrics: List[Dict[str, Any]], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Transform lyrics structure and embed metadata."""
    transformed = []
    for lyric_section in source_lyrics:
        transformed.append({
            'label': lyric_section['section'],
            'lines': lyric_section['lines']
        })
    transformed.append({'_metadata': metadata})
    return transformed


def transform_progression_section(prog: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a single progression section to database format."""
    chords = []
    for column in prog.get('columns', []):
        measures = column.get('measures', [])
        chords.extend(measures)

    return {
        'label': prog.get('section', 'Unknown'),
        'rows': 8,
        'endings': None,
        'chords': chords
    }


def flatten_chord_progression(
    chord_progression: List[Dict[str, Any]],
    song_keys: List[str]
) -> List[Dict[str, Any]]:
    """Flatten chord progression from columns/measures to flat chords array."""
    keys_output = []
    progressions_with_keys = [p for p in chord_progression if 'key' in p]

    if progressions_with_keys:
        key_groups: Dict[str, List[Dict[str, Any]]] = {}
        for prog in chord_progression:
            if 'key' not in prog:
                continue
            key = prog['key']
            if key not in key_groups:
                key_groups[key] = []
            key_groups[key].append(prog)

        for key, progs in key_groups.items():
            sections = []
            for prog in progs:
                section = transform_progression_section(prog)
                sections.append(section)
            keys_output.append({'key': key, 'sections': sections})
    else:
        for key in song_keys:
            sections = []
            for prog in chord_progression:
                section = transform_progression_section(prog)
                sections.append(section)
            keys_output.append({'key': key, 'sections': sections})

    return keys_output


def transform_song(song: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a song from source JSON to database schema."""
    if not song.get('title'):
        raise ValueError("Song missing required 'title' field")
    if not song.get('keys'):
        raise ValueError(f"Song '{song['title']}' missing required 'keys' field")
    if not song.get('chord_progression'):
        raise ValueError(f"Song '{song['title']}' missing required 'chord_progression' field")

    metadata = {
        'alternate_titles': song.get('alternate_titles', []),
        'artist': song.get('artist'),
        'source': song.get('source', 'imported'),
        'status': song.get('status', 'approved')
    }

    transformed_lyrics = transform_lyrics(song.get('lyrics', []), metadata)
    transformed_keys = flatten_chord_progression(song['chord_progression'], song['keys'])

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


def validate_songbook(source_file: str) -> dict:
    """Validate songbook transformations without database."""
    print(f"Loading songbook from {source_file}")

    with open(source_file, 'r') as f:
        data = json.load(f)

    songs = data.get('songbook', {}).get('songs', [])
    print(f"Found {len(songs)} songs to validate\n")

    results = {'valid': 0, 'invalid': 0, 'errors': [], 'songs': []}

    for idx, song in enumerate(songs, 1):
        title = song.get('title', f'Unknown #{idx}')
        try:
            print(f"[{idx}/{len(songs)}] Validating '{title}'")

            transformed = transform_song(song)

            # Validate structure
            assert transformed['guild_id'] == DEFAULT_GUILD_ID
            assert transformed['created_by'] == SYSTEM_USER_ID
            assert transformed['title'] == title
            assert len(transformed['keys']) > 0

            for key_entry in transformed['keys']:
                assert 'key' in key_entry
                assert 'sections' in key_entry
                for section in key_entry['sections']:
                    assert section['rows'] == 8
                    assert isinstance(section['chords'], list)

            has_metadata = any('_metadata' in l for l in transformed['lyrics'])
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
    print("=" * 60)
    print("TNBGJ SONGBOOK VALIDATION (DRY RUN)")
    print("=" * 60)
    print()

    results = validate_songbook(SOURCE_FILE)

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

    if results['invalid'] > 0:
        sys.exit(1)

    print(f"\n✓ All {results['valid']} songs validated successfully!")
    print("Ready for database import.")
    sys.exit(0)


if __name__ == '__main__':
    main()
