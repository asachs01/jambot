"""
Comprehensive test suite for TNBGJ songbook import script.

Tests cover:
- Chord progression flattening (columns -> chords array)
- Lyrics section rename (section -> label)
- Metadata embedding in JSONB
- Multi-key song handling
- Error handling for malformed data
- End-to-end import with database mocking
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from import_tnbgj_songbook import (
    transform_lyrics,
    flatten_chord_progression,
    transform_progression_section,
    transform_song,
    import_songbook,
    DEFAULT_GUILD_ID,
    SYSTEM_USER_ID
)


class TestTransformLyrics:
    """Test lyrics transformation logic."""

    def test_basic_transformation(self):
        """Test section -> label rename."""
        source = [
            {'section': 'verse', 'lines': ['Line 1', 'Line 2']},
            {'section': 'chorus', 'lines': ['Chorus line']}
        ]
        metadata = {'artist': 'Test Artist', 'source': 'imported'}

        result = transform_lyrics(source, metadata)

        # Check transformation (excluding metadata entry)
        lyrics_only = [r for r in result if '_metadata' not in r]
        assert len(lyrics_only) == 2
        assert lyrics_only[0] == {'label': 'verse', 'lines': ['Line 1', 'Line 2']}
        assert lyrics_only[1] == {'label': 'chorus', 'lines': ['Chorus line']}

    def test_metadata_embedding(self):
        """Test metadata embedded as final entry."""
        source = [{'section': 'verse', 'lines': ['Test']}]
        metadata = {
            'alternate_titles': ['Alt Title'],
            'artist': 'Bill Monroe',
            'source': 'imported',
            'status': 'approved'
        }

        result = transform_lyrics(source, metadata)

        # Find metadata entry
        metadata_entry = [r for r in result if '_metadata' in r]
        assert len(metadata_entry) == 1
        assert metadata_entry[0]['_metadata'] == metadata

    def test_empty_lyrics(self):
        """Test with empty lyrics list."""
        result = transform_lyrics([], {'source': 'test'})

        # Should only contain metadata entry
        assert len(result) == 1
        assert '_metadata' in result[0]


class TestProgressionFlattening:
    """Test chord progression transformation."""

    def test_single_key_no_explicit_key_field(self):
        """Test progression without explicit key field (infer from song.keys)."""
        progression = [
            {
                'section': 'A Part',
                'columns': [
                    {'label': '1', 'measures': ['D', 'D', 'D', 'D']},
                    {'label': '2', 'measures': ['G', 'G', 'D', 'D']}
                ]
            }
        ]
        song_keys = ['D']

        result = flatten_chord_progression(progression, song_keys)

        assert len(result) == 1
        assert result[0]['key'] == 'D'
        assert len(result[0]['sections']) == 1
        assert result[0]['sections'][0]['label'] == 'A Part'
        # Chords should be flattened in column order
        assert result[0]['sections'][0]['chords'] == ['D', 'D', 'D', 'D', 'G', 'G', 'D', 'D']
        assert result[0]['sections'][0]['rows'] == 8
        assert result[0]['sections'][0]['endings'] is None

    def test_multi_key_explicit_key_fields(self):
        """Test multi-key song with explicit key fields in progressions."""
        progression = [
            {
                'section': 'Verse/Chorus',
                'key': 'G',
                'columns': [
                    {'label': '1', 'measures': ['G', 'D', 'C', 'C']},
                    {'label': '2', 'measures': ['G', 'D', 'G', 'G']}
                ]
            },
            {
                'section': 'Verse/Chorus',
                'key': 'A',
                'columns': [
                    {'label': '1', 'measures': ['A', 'E', 'D', 'D']},
                    {'label': '2', 'measures': ['A', 'E', 'A', 'A']}
                ]
            }
        ]
        song_keys = ['G', 'A']

        result = flatten_chord_progression(progression, song_keys)

        assert len(result) == 2

        # Check G key entry
        g_entry = [r for r in result if r['key'] == 'G'][0]
        assert len(g_entry['sections']) == 1
        assert g_entry['sections'][0]['chords'] == ['G', 'D', 'C', 'C', 'G', 'D', 'G', 'G']

        # Check A key entry
        a_entry = [r for r in result if r['key'] == 'A'][0]
        assert len(a_entry['sections']) == 1
        assert a_entry['sections'][0]['chords'] == ['A', 'E', 'D', 'D', 'A', 'E', 'A', 'A']

    def test_multi_key_no_explicit_key_field(self):
        """Test multi-key song without explicit key fields (duplicate progressions)."""
        progression = [
            {
                'section': 'Verse',
                'columns': [
                    {'label': '1', 'measures': ['X', 'Y', 'Z', 'W']}
                ]
            }
        ]
        song_keys = ['G', 'A']

        result = flatten_chord_progression(progression, song_keys)

        # Should create separate key entries with identical progressions
        assert len(result) == 2
        assert result[0]['key'] == 'G'
        assert result[1]['key'] == 'A'
        assert result[0]['sections'][0]['chords'] == ['X', 'Y', 'Z', 'W']
        assert result[1]['sections'][0]['chords'] == ['X', 'Y', 'Z', 'W']

    def test_multiple_sections_same_key(self):
        """Test multiple progression sections for same key."""
        progression = [
            {
                'section': 'A Part',
                'columns': [{'label': '1', 'measures': ['D', 'D']}]
            },
            {
                'section': 'B Part',
                'columns': [{'label': '1', 'measures': ['G', 'G']}]
            }
        ]
        song_keys = ['D']

        result = flatten_chord_progression(progression, song_keys)

        assert len(result) == 1
        assert len(result[0]['sections']) == 2
        assert result[0]['sections'][0]['label'] == 'A Part'
        assert result[0]['sections'][1]['label'] == 'B Part'

    def test_varying_column_counts(self):
        """Test progressions with different numbers of columns."""
        progression = [
            {
                'section': 'Verse',
                'columns': [
                    {'label': '1', 'measures': ['A', 'B']},
                    {'label': '2', 'measures': ['C', 'D']},
                    {'label': '3', 'measures': ['E', 'F']}
                ]
            }
        ]
        song_keys = ['G']

        result = flatten_chord_progression(progression, song_keys)

        # Should concatenate all columns in order
        assert result[0]['sections'][0]['chords'] == ['A', 'B', 'C', 'D', 'E', 'F']


class TestTransformProgressionSection:
    """Test single progression section transformation."""

    def test_basic_section_transform(self):
        """Test basic section transformation."""
        section = {
            'section': 'Intro',
            'columns': [
                {'label': '1', 'measures': ['G', 'G', 'C', 'C']},
                {'label': '2', 'measures': ['G', 'D', 'G', 'G']}
            ]
        }

        result = transform_progression_section(section)

        assert result['label'] == 'Intro'
        assert result['rows'] == 8
        assert result['endings'] is None
        assert result['chords'] == ['G', 'G', 'C', 'C', 'G', 'D', 'G', 'G']

    def test_missing_section_name(self):
        """Test section without name."""
        section = {
            'columns': [{'label': '1', 'measures': ['D', 'D']}]
        }

        result = transform_progression_section(section)

        assert result['label'] == 'Unknown'

    def test_empty_columns(self):
        """Test section with no columns."""
        section = {
            'section': 'Empty',
            'columns': []
        }

        result = transform_progression_section(section)

        assert result['chords'] == []


class TestTransformSong:
    """Test complete song transformation."""

    def test_single_key_song(self):
        """Test transforming a single-key song (Angeline the Baker)."""
        song = {
            'title': 'Angeline the Baker',
            'artist': None,
            'alternate_titles': [],
            'keys': ['D'],
            'source': 'imported',
            'status': 'approved',
            'lyrics': [
                {'section': 'verse', 'lines': ['Line 1', 'Line 2']}
            ],
            'chord_progression': [
                {
                    'section': 'A Part',
                    'columns': [
                        {'label': '1', 'measures': ['D', 'D', 'G', 'D']}
                    ]
                }
            ]
        }

        result = transform_song(song)

        assert result['guild_id'] == DEFAULT_GUILD_ID
        assert result['created_by'] == SYSTEM_USER_ID
        assert result['title'] == 'Angeline the Baker'
        assert result['chart_title'] == 'Angeline the Baker'
        assert len(result['keys']) == 1
        assert result['keys'][0]['key'] == 'D'

        # Check lyrics transformation
        lyrics_data = [l for l in result['lyrics'] if '_metadata' not in l]
        assert lyrics_data[0]['label'] == 'verse'

        # Check metadata
        metadata_entry = [l for l in result['lyrics'] if '_metadata' in l][0]
        assert metadata_entry['_metadata']['source'] == 'imported'
        assert metadata_entry['_metadata']['status'] == 'approved'
        assert metadata_entry['_metadata']['artist'] is None

    def test_multi_key_song_with_explicit_keys(self):
        """Test transforming multi-key song (Blue Ridge Cabin Home)."""
        song = {
            'title': 'Blue Ridge Cabin Home',
            'artist': None,
            'alternate_titles': ['Blueridge Cabin Home'],
            'keys': ['G', 'A'],
            'source': 'imported',
            'status': 'approved',
            'lyrics': [
                {'section': 'verse', 'lines': ['Test verse']}
            ],
            'chord_progression': [
                {
                    'section': 'Verse/Chorus',
                    'key': 'G',
                    'columns': [
                        {'label': '1', 'measures': ['G', 'D', 'C', 'C']}
                    ]
                },
                {
                    'section': 'Verse/Chorus',
                    'key': 'A',
                    'columns': [
                        {'label': '1', 'measures': ['A', 'E', 'D', 'D']}
                    ]
                }
            ]
        }

        result = transform_song(song)

        # Should have 2 key entries
        assert len(result['keys']) == 2
        keys_dict = {k['key']: k for k in result['keys']}
        assert 'G' in keys_dict
        assert 'A' in keys_dict

        # Check alternate titles in metadata
        metadata_entry = [l for l in result['lyrics'] if '_metadata' in l][0]
        assert metadata_entry['_metadata']['alternate_titles'] == ['Blueridge Cabin Home']

    def test_long_title_abbreviation(self):
        """Test chart_title abbreviation for long titles."""
        song = {
            'title': 'This Is A Very Long Song Title That Exceeds Twenty Characters',
            'keys': ['G'],
            'chord_progression': [
                {
                    'section': 'Test',
                    'columns': [{'label': '1', 'measures': ['G']}]
                }
            ],
            'lyrics': []
        }

        result = transform_song(song)

        assert len(result['chart_title']) <= 20
        assert result['chart_title'].endswith('...')
        assert result['chart_title'] == 'This Is A Very Lo...'

    def test_missing_title_raises_error(self):
        """Test that missing title raises ValueError."""
        song = {
            'keys': ['G'],
            'chord_progression': [{'section': 'Test', 'columns': []}],
            'lyrics': []
        }

        with pytest.raises(ValueError, match="missing required 'title'"):
            transform_song(song)

    def test_missing_keys_raises_error(self):
        """Test that missing keys raises ValueError."""
        song = {
            'title': 'Test Song',
            'chord_progression': [{'section': 'Test', 'columns': []}],
            'lyrics': []
        }

        with pytest.raises(ValueError, match="missing required 'keys'"):
            transform_song(song)

    def test_missing_chord_progression_raises_error(self):
        """Test that missing chord_progression raises ValueError."""
        song = {
            'title': 'Test Song',
            'keys': ['G'],
            'lyrics': []
        }

        with pytest.raises(ValueError, match="missing required 'chord_progression'"):
            transform_song(song)

    def test_artist_with_value(self):
        """Test song with artist metadata (Blue Moon of Kentucky)."""
        song = {
            'title': 'Blue Moon of Kentucky',
            'artist': 'Bill Monroe',
            'alternate_titles': ['Blue Moon of Ky'],
            'keys': ['C'],
            'source': 'imported',
            'status': 'approved',
            'lyrics': [{'section': 'verse', 'lines': ['Blue moon...']}],
            'chord_progression': [
                {
                    'section': 'A Part',
                    'columns': [{'label': '1', 'measures': ['C', 'F', 'G', 'C']}]
                }
            ]
        }

        result = transform_song(song)

        metadata_entry = [l for l in result['lyrics'] if '_metadata' in l][0]
        assert metadata_entry['_metadata']['artist'] == 'Bill Monroe'
        assert metadata_entry['_metadata']['alternate_titles'] == ['Blue Moon of Ky']

    def test_empty_alternate_titles(self):
        """Test song with empty alternate_titles array."""
        song = {
            'title': 'Test Song',
            'artist': None,
            'alternate_titles': [],
            'keys': ['G'],
            'source': 'imported',
            'status': 'approved',
            'lyrics': [],
            'chord_progression': [
                {
                    'section': 'Test',
                    'columns': [{'label': '1', 'measures': ['G']}]
                }
            ]
        }

        result = transform_song(song)

        metadata_entry = [l for l in result['lyrics'] if '_metadata' in l][0]
        assert metadata_entry['_metadata']['alternate_titles'] == []


class TestImportSongbook:
    """Test end-to-end import functionality."""

    def test_successful_import(self, tmp_path):
        """Test successful import of valid songbook."""
        # Create test JSON file
        test_data = {
            'songbook': {
                'name': 'Test Songbook',
                'songs': [
                    {
                        'title': 'Test Song 1',
                        'keys': ['G'],
                        'lyrics': [{'section': 'verse', 'lines': ['Line 1']}],
                        'chord_progression': [
                            {
                                'section': 'Verse',
                                'columns': [{'label': '1', 'measures': ['G', 'C', 'D', 'G']}]
                            }
                        ]
                    },
                    {
                        'title': 'Test Song 2',
                        'keys': ['D'],
                        'lyrics': [{'section': 'chorus', 'lines': ['Chorus line']}],
                        'chord_progression': [
                            {
                                'section': 'Chorus',
                                'columns': [{'label': '1', 'measures': ['D', 'A', 'D', 'D']}]
                            }
                        ]
                    }
                ]
            }
        }

        test_file = tmp_path / 'test_songbook.json'
        test_file.write_text(json.dumps(test_data))

        # Mock database
        mock_db = Mock()
        mock_db.create_chord_chart.side_effect = [1, 2]  # Return chart IDs

        # Run import
        results = import_songbook(str(test_file), mock_db)

        assert results['succeeded'] == 2
        assert results['failed'] == 0
        assert results['skipped'] == 0
        assert len(results['errors']) == 0
        assert mock_db.create_chord_chart.call_count == 2

    def test_import_with_validation_error(self, tmp_path):
        """Test import with validation errors (missing fields)."""
        test_data = {
            'songbook': {
                'songs': [
                    {
                        'title': 'Valid Song',
                        'keys': ['G'],
                        'chord_progression': [
                            {'section': 'Test', 'columns': [{'label': '1', 'measures': ['G']}]}
                        ]
                    },
                    {
                        # Missing title
                        'keys': ['D'],
                        'chord_progression': [
                            {'section': 'Test', 'columns': [{'label': '1', 'measures': ['D']}]}
                        ]
                    },
                    {
                        'title': 'Missing Keys',
                        # Missing keys field
                        'chord_progression': [
                            {'section': 'Test', 'columns': [{'label': '1', 'measures': ['A']}]}
                        ]
                    }
                ]
            }
        }

        test_file = tmp_path / 'test_songbook.json'
        test_file.write_text(json.dumps(test_data))

        mock_db = Mock()
        mock_db.create_chord_chart.return_value = 1

        results = import_songbook(str(test_file), mock_db)

        assert results['succeeded'] == 1
        assert results['skipped'] == 2
        assert results['failed'] == 0
        assert len(results['errors']) == 2

    def test_import_with_database_error(self, tmp_path):
        """Test import with database errors."""
        test_data = {
            'songbook': {
                'songs': [
                    {
                        'title': 'Song That Fails',
                        'keys': ['G'],
                        'chord_progression': [
                            {'section': 'Test', 'columns': [{'label': '1', 'measures': ['G']}]}
                        ]
                    }
                ]
            }
        }

        test_file = tmp_path / 'test_songbook.json'
        test_file.write_text(json.dumps(test_data))

        mock_db = Mock()
        mock_db.create_chord_chart.side_effect = Exception("Database connection failed")

        results = import_songbook(str(test_file), mock_db)

        assert results['succeeded'] == 0
        assert results['failed'] == 1
        assert len(results['errors']) == 1
        assert 'Database connection failed' in results['errors'][0]['error']

    def test_idempotency(self, tmp_path):
        """Test that re-importing same data calls upsert correctly."""
        test_data = {
            'songbook': {
                'songs': [
                    {
                        'title': 'Duplicate Song',
                        'keys': ['G'],
                        'chord_progression': [
                            {'section': 'Test', 'columns': [{'label': '1', 'measures': ['G']}]}
                        ]
                    }
                ]
            }
        }

        test_file = tmp_path / 'test_songbook.json'
        test_file.write_text(json.dumps(test_data))

        mock_db = Mock()
        mock_db.create_chord_chart.return_value = 1

        # First import
        results1 = import_songbook(str(test_file), mock_db)
        assert results1['succeeded'] == 1

        # Second import (idempotent)
        results2 = import_songbook(str(test_file), mock_db)
        assert results2['succeeded'] == 1

        # Should call create_chord_chart twice (relies on upsert)
        assert mock_db.create_chord_chart.call_count == 2


class TestIntegrationScenarios:
    """Integration tests with real song data structures."""

    def test_angeline_the_baker(self):
        """Test with real Angeline the Baker data."""
        song = {
            'title': 'Angeline the Baker',
            'artist': None,
            'alternate_titles': [],
            'keys': ['D'],
            'source': 'imported',
            'status': 'approved',
            'lyrics': [
                {
                    'section': 'verse',
                    'lines': [
                        'Angeline the Baker, her age was forty-three,',
                        "Should have married Angeline when she'd have married me."
                    ]
                }
            ],
            'chord_progression': [
                {
                    'section': 'A Part',
                    'columns': [
                        {'label': '1', 'measures': ['D', 'D', 'D', 'D', 'D', 'G', 'G', 'D']},
                        {'label': '2', 'measures': ['D', 'D', 'D', 'D', 'D', 'D', 'G', 'D']}
                    ]
                },
                {
                    'section': 'B Part',
                    'columns': [
                        {'label': '1', 'measures': ['D', 'D', 'D', 'D', 'D', 'G', 'G', 'G']},
                        {'label': '2', 'measures': ['D', 'D', 'D', 'D', 'D', 'G', 'D', 'D']}
                    ]
                }
            ]
        }

        result = transform_song(song)

        # Verify structure
        assert result['title'] == 'Angeline the Baker'
        assert len(result['keys']) == 1
        assert result['keys'][0]['key'] == 'D'
        assert len(result['keys'][0]['sections']) == 2

        # Verify chord flattening
        a_part = result['keys'][0]['sections'][0]
        assert a_part['label'] == 'A Part'
        assert a_part['chords'] == ['D', 'D', 'D', 'D', 'D', 'G', 'G', 'D',
                                     'D', 'D', 'D', 'D', 'D', 'D', 'G', 'D']

    def test_blue_ridge_cabin_home(self):
        """Test with real Blue Ridge Cabin Home data (multi-key)."""
        song = {
            'title': 'Blue Ridge Cabin Home',
            'artist': None,
            'alternate_titles': ['Blueridge Cabin Home'],
            'keys': ['G', 'A'],
            'source': 'imported',
            'status': 'approved',
            'lyrics': [
                {
                    'section': 'verse',
                    'lines': ["There's a well beaten path in the old mountainside"]
                },
                {
                    'section': 'chorus',
                    'lines': ['Oh I love those hills of old Virginia']
                }
            ],
            'chord_progression': [
                {
                    'section': 'Verse/Chorus',
                    'key': 'G',
                    'columns': [
                        {'label': '1', 'measures': ['G', 'D', 'G', 'D', 'C', 'C', 'C', 'C']},
                        {'label': '2', 'measures': ['G', 'D', 'G', 'D', 'G', 'G', 'G', 'G']}
                    ]
                },
                {
                    'section': 'Verse/Chorus',
                    'key': 'A',
                    'columns': [
                        {'label': '1', 'measures': ['A', 'E', 'A', 'E', 'D', 'D', 'D', 'D']},
                        {'label': '2', 'measures': ['A', 'E', 'A', 'E', 'A', 'A', 'A', 'A']}
                    ]
                }
            ]
        }

        result = transform_song(song)

        # Should have 2 key entries
        assert len(result['keys']) == 2
        keys_dict = {k['key']: k for k in result['keys']}

        # Verify G key
        assert 'G' in keys_dict
        g_section = keys_dict['G']['sections'][0]
        assert g_section['label'] == 'Verse/Chorus'
        assert g_section['chords'][:4] == ['G', 'D', 'G', 'D']

        # Verify A key
        assert 'A' in keys_dict
        a_section = keys_dict['A']['sections'][0]
        assert a_section['label'] == 'Verse/Chorus'
        assert a_section['chords'][:4] == ['A', 'E', 'A', 'E']

        # Verify lyrics
        lyrics_data = [l for l in result['lyrics'] if '_metadata' not in l]
        assert len(lyrics_data) == 2
        assert lyrics_data[0]['label'] == 'verse'
        assert lyrics_data[1]['label'] == 'chorus'
