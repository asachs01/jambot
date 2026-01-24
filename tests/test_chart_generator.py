"""Tests for chord chart generation and transposition logic."""
import pytest
from src.chart_generator import (
    parse_chord,
    note_to_index,
    index_to_note,
    should_use_flats,
    transpose_chord,
    transpose_key_entry,
    parse_chord_input,
    generate_chart_pdf,
    SHARPS,
    FLATS,
)


# --- parse_chord ---

class TestParseChord:
    def test_major_chord(self):
        assert parse_chord('G') == {'root': 'G', 'quality': ''}

    def test_minor_chord(self):
        assert parse_chord('Am') == {'root': 'A', 'quality': 'm'}

    def test_seventh_chord(self):
        assert parse_chord('D7') == {'root': 'D', 'quality': '7'}

    def test_sharp_minor_seventh(self):
        assert parse_chord('F#m7') == {'root': 'F#', 'quality': 'm7'}

    def test_flat_chord(self):
        assert parse_chord('Bb') == {'root': 'Bb', 'quality': ''}

    def test_suspended(self):
        assert parse_chord('Dsus4') == {'root': 'D', 'quality': 'sus4'}

    def test_invalid_returns_none(self):
        assert parse_chord('X') is None
        assert parse_chord('') is None
        assert parse_chord('123') is None

    def test_whitespace_stripped(self):
        assert parse_chord('  G  ') == {'root': 'G', 'quality': ''}


# --- note_to_index ---

class TestNoteToIndex:
    def test_all_sharps(self):
        for i, note in enumerate(SHARPS):
            assert note_to_index(note) == i

    def test_all_flats(self):
        for i, note in enumerate(FLATS):
            assert note_to_index(note) == i

    def test_invalid_returns_negative(self):
        assert note_to_index('X') == -1
        assert note_to_index('H') == -1


# --- index_to_note ---

class TestIndexToNote:
    def test_basic_sharps(self):
        assert index_to_note(0) == 'C'
        assert index_to_note(7) == 'G'

    def test_basic_flats(self):
        assert index_to_note(1, use_flats=True) == 'Db'
        assert index_to_note(3, use_flats=True) == 'Eb'

    def test_wraps_positive(self):
        assert index_to_note(12) == 'C'
        assert index_to_note(14) == 'D'

    def test_wraps_negative(self):
        assert index_to_note(-1) == 'B'
        assert index_to_note(-2) == 'A#'
        assert index_to_note(-2, use_flats=True) == 'Bb'


# --- should_use_flats ---

class TestShouldUseFlats:
    def test_flat_keys(self):
        for key in ['F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb']:
            assert should_use_flats(key) is True

    def test_sharp_keys(self):
        for key in ['G', 'D', 'A', 'E', 'B', 'F#']:
            assert should_use_flats(key) is False

    def test_c_uses_flats(self):
        # C is in FLAT_KEYS (convention: C major has no sharps/flats,
        # but we default to flats for consistency)
        assert should_use_flats('C') is True

    def test_unknown_defaults_false(self):
        assert should_use_flats('X') is False


# --- transpose_chord ---

class TestTransposeChord:
    def test_up_whole_step(self):
        assert transpose_chord('G', 2) == 'A'

    def test_down_whole_step(self):
        assert transpose_chord('D', -2) == 'C'

    def test_no_change(self):
        assert transpose_chord('E', 0) == 'E'

    def test_wraps_around(self):
        assert transpose_chord('B', 1) == 'C'

    def test_preserves_minor(self):
        assert transpose_chord('Am', 2) == 'Bm'

    def test_preserves_seventh(self):
        assert transpose_chord('D7', 5) == 'G7'

    def test_preserves_minor_seventh(self):
        assert transpose_chord('Em7', 5) == 'Am7'

    def test_sharp_spelling(self):
        assert transpose_chord('C', 1, use_flats=False) == 'C#'

    def test_flat_spelling(self):
        assert transpose_chord('C', 1, use_flats=True) == 'Db'

    def test_invalid_chord_passthrough(self):
        assert transpose_chord('N.C.', 2) == 'N.C.'
        assert transpose_chord('', 2) == ''

    def test_full_octave_returns_same(self):
        assert transpose_chord('G', 12) == 'G'
        assert transpose_chord('Am', 12) == 'Am'

    @pytest.mark.parametrize("semitones", range(12))
    def test_all_semitones_from_c(self, semitones):
        result = transpose_chord('C', semitones)
        assert result in SHARPS  # All should be valid notes


# --- transpose_key_entry ---

class TestTransposeKeyEntry:
    def test_g_to_a(self):
        key_entry = {
            'key': 'G',
            'sections': [{
                'label': 'Verse',
                'rows': 1,
                'endings': None,
                'chords': ['G', 'C', 'D', 'G'],
            }]
        }
        result = transpose_key_entry(key_entry, 'A')
        assert result['key'] == 'A'
        assert result['sections'][0]['chords'] == ['A', 'D', 'E', 'A']

    def test_preserves_structure(self):
        key_entry = {
            'key': 'C',
            'sections': [
                {'label': 'A Part', 'rows': 2, 'endings': None, 'chords': ['C', 'F', 'G', 'C']},
                {'label': 'B Part', 'rows': 1, 'endings': None, 'chords': ['Am', 'Dm', 'G7', 'C']},
            ]
        }
        result = transpose_key_entry(key_entry, 'D')
        assert len(result['sections']) == 2
        assert result['sections'][0]['label'] == 'A Part'
        assert result['sections'][1]['chords'] == ['Bm', 'Em', 'A7', 'D']

    def test_to_flat_key(self):
        key_entry = {
            'key': 'G',
            'sections': [{'label': 'V', 'rows': 1, 'endings': None, 'chords': ['G', 'C', 'D']}]
        }
        result = transpose_key_entry(key_entry, 'F')
        assert result['sections'][0]['chords'] == ['F', 'Bb', 'C']

    def test_empty_sections(self):
        key_entry = {'key': 'G', 'sections': []}
        result = transpose_key_entry(key_entry, 'A')
        assert result == {'key': 'A', 'sections': []}


# --- parse_chord_input ---

class TestParseChordInput:
    def test_basic_two_sections(self):
        data = parse_chord_input(
            title='Mountain Dew',
            key='G',
            section_labels='Verse,Chorus',
            chords_text='G G C G | D D G G\n\nC C G G | D D G G',
        )
        assert data['title'] == 'Mountain Dew'
        assert data['keys'][0]['key'] == 'G'
        assert len(data['keys'][0]['sections']) == 2
        assert data['keys'][0]['sections'][0]['label'] == 'Verse'
        assert data['keys'][0]['sections'][1]['label'] == 'Chorus'
        assert data['lyrics'] is None

    def test_with_lyrics(self):
        data = parse_chord_input(
            title='Test',
            key='D',
            section_labels='Verse',
            chords_text='D G A D',
            lyrics_text='Line one\nLine two',
        )
        assert data['lyrics'] is not None
        assert len(data['lyrics']) == 1
        assert data['lyrics'][0]['lines'] == ['Line one', 'Line two']

    def test_pipe_separated_measures(self):
        data = parse_chord_input(
            title='Test',
            key='G',
            section_labels='A',
            chords_text='G C | D G',
        )
        chords = data['keys'][0]['sections'][0]['chords']
        assert chords == ['G', 'C', 'D', 'G']

    def test_chart_title_truncation(self):
        long_title = 'A Very Long Song Title That Exceeds Twenty Characters'
        data = parse_chord_input(
            title=long_title,
            key='G',
            section_labels='A',
            chords_text='G C D G',
        )
        assert len(data['chart_title']) <= 20

    def test_extra_sections_get_default_labels(self):
        data = parse_chord_input(
            title='Test',
            key='G',
            section_labels='Verse',  # Only one label
            chords_text='G C D G\n\nA D E A',  # Two sections
        )
        assert data['keys'][0]['sections'][1]['label'] == 'Section 2'

    def test_empty_lyrics_ignored(self):
        data = parse_chord_input(
            title='Test',
            key='G',
            section_labels='A',
            chords_text='G C D G',
            lyrics_text='   ',
        )
        assert data['lyrics'] is None


# --- generate_chart_pdf ---

class TestGenerateChartPdf:
    def test_produces_valid_pdf(self):
        data = parse_chord_input(
            title='Test Song',
            key='G',
            section_labels='Verse,Chorus',
            chords_text='G G C G | D D G G\n\nC C G G | D D G G',
            lyrics_text='First verse\n\nChorus line',
        )
        pdf_buf = generate_chart_pdf(data)
        pdf_bytes = pdf_buf.read()
        assert pdf_bytes[:4] == b'%PDF'
        assert len(pdf_bytes) > 500  # Should be non-trivial

    def test_no_lyrics(self):
        data = parse_chord_input(
            title='Instrumental',
            key='D',
            section_labels='A Part',
            chords_text='D G A D',
        )
        pdf_buf = generate_chart_pdf(data)
        assert pdf_buf.read()[:4] == b'%PDF'

    def test_multiple_keys(self):
        data = parse_chord_input(
            title='Multi Key',
            key='G',
            section_labels='Verse',
            chords_text='G C D G',
        )
        # Add a transposed key
        transposed = transpose_key_entry(data['keys'][0], 'A')
        data['keys'].append(transposed)

        pdf_buf = generate_chart_pdf(data)
        assert pdf_buf.read()[:4] == b'%PDF'

    def test_empty_chart(self):
        data = {
            'title': 'Empty',
            'chart_title': 'Empty',
            'keys': [],
            'lyrics': None,
        }
        pdf_buf = generate_chart_pdf(data)
        assert pdf_buf.read()[:4] == b'%PDF'

    def test_many_chords(self):
        # Stress test with a long progression
        chords = ' '.join(['G', 'C', 'D', 'Em'] * 16)
        data = parse_chord_input(
            title='Long Song',
            key='G',
            section_labels='Verse',
            chords_text=chords,
        )
        pdf_buf = generate_chart_pdf(data)
        assert pdf_buf.read()[:4] == b'%PDF'


# --- Integration: transpose + PDF ---

class TestTransposeAndRender:
    @pytest.mark.parametrize("target_key", ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'Bb', 'Eb', 'F#'])
    def test_transpose_to_all_common_keys(self, target_key):
        data = parse_chord_input(
            title='Key Test',
            key='G',
            section_labels='Verse',
            chords_text='G Am C D7',
        )
        transposed = transpose_key_entry(data['keys'][0], target_key)
        data['keys'] = [transposed]

        pdf_buf = generate_chart_pdf(data)
        pdf_bytes = pdf_buf.read()
        assert pdf_bytes[:4] == b'%PDF'
        assert transposed['key'] == target_key
