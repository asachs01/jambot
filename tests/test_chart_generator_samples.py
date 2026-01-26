"""Generate sample PDF chord charts for visual verification.

Run with: pytest tests/test_chart_generator_samples.py -v --save-samples

This generates sample PDFs in tests/samples/ for each chart format/style.
"""
import os
import pytest
from pathlib import Path

from src.chart_generator import (
    parse_chord_input,
    transpose_key_entry,
    generate_chart_pdf,
)


# Sample directory for generated PDFs
SAMPLES_DIR = Path(__file__).parent / "samples"


@pytest.fixture
def save_samples(request):
    """Fixture to check if samples should be saved."""
    return request.config.getoption("--save-samples", default=False)


def save_pdf(pdf_buffer, filename: str, force: bool = False):
    """Save a PDF buffer to the samples directory."""
    if not force:
        return
    SAMPLES_DIR.mkdir(exist_ok=True)
    filepath = SAMPLES_DIR / filename
    with open(filepath, "wb") as f:
        f.write(pdf_buffer.read())
    pdf_buffer.seek(0)  # Reset for any subsequent reads
    print(f"\nSaved: {filepath}")


class TestTNBGJFormatSamples:
    """Generate samples of the TNBGJ chord chart format."""

    def test_blue_ridge_cabin_home(self, save_samples):
        """Classic bluegrass song in G and A - the reference example."""
        data = parse_chord_input(
            title="Blue Ridge Cabin Home",
            key="G",
            section_labels="Verse/Chorus",
            chords_text="""
                G G G G G G D D
                G G G G C C C C
                G G G G G G D D
                D D D D G G G G
            """,
            lyrics_text="""There's a well beaten path in the old mountainside
Where I wandered when I was a lad
And I wandered alone to the place I call home
In those Blueridge hills far away

Oh I love those hills of old Virginia
From those Blueridge hills I did roam
When I die won't you bury me on the mountain
Far away near my Blueridge mountain home

Now my thoughts wander back to that ramshackle shack
In those blue ridge hills far away
Where my mother and dad were laid there to rest
They are sleeping in peace together there

I return to that old cabin home with the sigh
I've been longing for days gone by
When I die won't you bury me on that old mountain side
Make my resting place upon the hills so high"""
        )

        # Add transposed key (A)
        transposed = transpose_key_entry(data['keys'][0], 'A')
        data['keys'].append(transposed)
        data['status'] = 'approved'

        pdf = generate_chart_pdf(data)
        assert pdf.read()[:4] == b'%PDF'
        pdf.seek(0)
        save_pdf(pdf, "tnbgj-blue-ridge-cabin-home.pdf", save_samples)

    def test_simple_song_draft(self, save_samples):
        """Simple song showing draft watermark."""
        data = parse_chord_input(
            title="Simple Draft Song",
            key="G",
            section_labels="Verse,Chorus",
            chords_text="""
                G C G D

                C G D G
            """,
            lyrics_text="""Verse lyrics go here
Line two of the verse
Line three
Final line

Chorus lyrics
Second line
Third line"""
        )
        data['status'] = 'draft'

        pdf = generate_chart_pdf(data)
        assert pdf.read()[:4] == b'%PDF'
        pdf.seek(0)
        save_pdf(pdf, "tnbgj-draft-example.pdf", save_samples)

    def test_instrumental(self, save_samples):
        """Instrumental tune with no lyrics (fiddle tune style)."""
        data = parse_chord_input(
            title="Old Joe Clark",
            key="A",
            section_labels="A Part,B Part",
            chords_text="""
                A A A A A A G G
                A A A A A A G A

                A A A A A A G G
                A A A A A A G A
            """,
        )
        # Add D key
        transposed = transpose_key_entry(data['keys'][0], 'D')
        data['keys'].append(transposed)
        data['status'] = 'approved'

        pdf = generate_chart_pdf(data)
        assert pdf.read()[:4] == b'%PDF'
        pdf.seek(0)
        save_pdf(pdf, "tnbgj-instrumental.pdf", save_samples)

    def test_multiple_keys_three(self, save_samples):
        """Song with three keys for maximum flexibility."""
        data = parse_chord_input(
            title="Wagon Wheel",
            key="A",
            section_labels="Verse,Chorus",
            chords_text="""
                A E F#m D
                A E D D

                A E F#m D
                A E D A
            """,
            lyrics_text="""Headed down south to the land of the pines
I'm thumbin' my way into North Caroline

So rock me mama like a wagon wheel
Rock me mama any way you feel"""
        )

        # Add G and C keys
        data['keys'].append(transpose_key_entry(data['keys'][0], 'G'))
        data['keys'].append(transpose_key_entry(data['keys'][0], 'C'))
        data['status'] = 'approved'

        pdf = generate_chart_pdf(data)
        assert pdf.read()[:4] == b'%PDF'
        pdf.seek(0)
        save_pdf(pdf, "tnbgj-three-keys.pdf", save_samples)

    def test_long_chord_progression(self, save_samples):
        """Complex song with long progression showing grid expansion."""
        # 64-chord progression (8 columns × 8 rows)
        chords = ['G', 'G', 'C', 'C', 'G', 'G', 'D', 'D'] * 4 + \
                 ['C', 'C', 'G', 'G', 'D', 'D', 'G', 'G'] * 4

        data = parse_chord_input(
            title="Long Song Example",
            key="G",
            section_labels="Full Progression",
            chords_text=' '.join(chords),
            lyrics_text="""This is a song with a very long chord progression
That requires many columns to display
The grid expands horizontally to fit all chords
While maintaining the column-major reading order"""
        )
        data['status'] = 'approved'

        pdf = generate_chart_pdf(data)
        assert pdf.read()[:4] == b'%PDF'
        pdf.seek(0)
        save_pdf(pdf, "tnbgj-long-progression.pdf", save_samples)

    def test_flat_key(self, save_samples):
        """Song in a flat key (F) to verify flat spelling."""
        data = parse_chord_input(
            title="Flat Key Song",
            key="F",
            section_labels="Verse",
            chords_text="""
                F F Bb Bb
                F F C C
                F F Bb Bb
                C C F F
            """,
            lyrics_text="""A song in F major
Using flats not sharps
Bb is the IV chord
C is the V chord"""
        )

        # Add Eb key (another flat key)
        data['keys'].append(transpose_key_entry(data['keys'][0], 'Eb'))
        data['status'] = 'approved'

        pdf = generate_chart_pdf(data)
        assert pdf.read()[:4] == b'%PDF'
        pdf.seek(0)
        save_pdf(pdf, "tnbgj-flat-keys.pdf", save_samples)


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    def test_very_long_title(self, save_samples):
        """Song with a very long title that needs truncation."""
        data = parse_chord_input(
            title="This Is An Extremely Long Song Title That Should Be Truncated In The Chart Area",
            key="G",
            section_labels="Verse",
            chords_text="G C D G",
        )
        data['status'] = 'approved'

        pdf = generate_chart_pdf(data)
        assert pdf.read()[:4] == b'%PDF'
        pdf.seek(0)
        save_pdf(pdf, "tnbgj-long-title.pdf", save_samples)

    def test_many_sections(self, save_samples):
        """Song with many distinct sections."""
        data = parse_chord_input(
            title="Multi-Section Song",
            key="D",
            section_labels="Intro,Verse 1,Chorus,Verse 2,Bridge,Chorus,Outro",
            chords_text="""
                D D A A

                D D G G A A D D

                G G D D A A D D

                D D G G A A D D

                Bm Bm G G A A A A

                G G D D A A D D

                D D D D
            """,
        )
        data['status'] = 'approved'

        pdf = generate_chart_pdf(data)
        assert pdf.read()[:4] == b'%PDF'
        pdf.seek(0)
        save_pdf(pdf, "tnbgj-many-sections.pdf", save_samples)

    def test_complex_chords(self, save_samples):
        """Song with complex jazz-style chords."""
        data = parse_chord_input(
            title="Jazz Chords Example",
            key="C",
            section_labels="Verse",
            chords_text="""
                Cmaj7 Cmaj7 Dm7 Dm7
                Em7 A7 Dm7 G7
                Cmaj7 Am7 Dm7 G7
                C6 C6 C6 C6
            """,
            lyrics_text="""Complex chord voicings
Seventh chords and extensions
Still readable in the grid
Jazz meets bluegrass format"""
        )
        data['status'] = 'approved'

        pdf = generate_chart_pdf(data)
        assert pdf.read()[:4] == b'%PDF'
        pdf.seek(0)
        save_pdf(pdf, "tnbgj-complex-chords.pdf", save_samples)

    def test_empty_chart(self, save_samples):
        """Empty chart (edge case)."""
        data = {
            'title': 'Empty Chart',
            'chart_title': 'Empty',
            'keys': [],
            'lyrics': None,
            'status': 'draft',
        }

        pdf = generate_chart_pdf(data)
        assert pdf.read()[:4] == b'%PDF'
        pdf.seek(0)
        save_pdf(pdf, "tnbgj-empty.pdf", save_samples)


# Allow running directly with: python -m pytest tests/test_chart_generator_samples.py -v --save-samples
if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v", "--save-samples"] + sys.argv[1:])
