"""Chord chart PDF generation and transposition for Jambot.

Generates landscape letter PDFs matching the TNBGJ songbook format:
- Left panel: title + lyrics
- Right panel: chord grid (column-major reading order)
"""
import io
import json
from typing import Dict, List, Optional, Any

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import black, white, HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from src.logger import logger

# --- Transposition Logic ---

SHARPS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLATS = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
SHARP_KEYS = {'G', 'D', 'A', 'E', 'B', 'F#', 'C#'}
FLAT_KEYS = {'F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'C'}


def parse_chord(chord: str) -> Optional[Dict[str, str]]:
    """Parse a chord string into root note and quality."""
    import re
    m = re.match(r'^([A-G][#b]?)(.*)', chord.strip())
    if not m:
        return None
    return {'root': m.group(1), 'quality': m.group(2)}


def note_to_index(note: str) -> int:
    """Convert a note name to chromatic index (0-11)."""
    if note in SHARPS:
        return SHARPS.index(note)
    if note in FLATS:
        return FLATS.index(note)
    return -1


def index_to_note(idx: int, use_flats: bool = False) -> str:
    """Convert a chromatic index to a note name."""
    idx = ((idx % 12) + 12) % 12
    return FLATS[idx] if use_flats else SHARPS[idx]


def should_use_flats(target_key: str) -> bool:
    """Determine whether to use flat spelling for a target key."""
    if target_key in FLAT_KEYS:
        return True
    if target_key in SHARP_KEYS:
        return False
    return False


def transpose_chord(chord: str, semitones: int, use_flats: bool = False) -> str:
    """Transpose a single chord by N semitones."""
    parsed = parse_chord(chord)
    if not parsed:
        return chord
    root_idx = note_to_index(parsed['root'])
    if root_idx < 0:
        return chord
    new_idx = root_idx + semitones
    new_root = index_to_note(new_idx, use_flats)
    return new_root + parsed['quality']


def transpose_key_entry(key_entry: Dict, target_key: str) -> Dict:
    """Transpose an entire key entry to a new key.

    Args:
        key_entry: Dict with 'key' and 'sections' list.
        target_key: Target key string (e.g. 'A').

    Returns:
        New key entry dict with transposed chords.
    """
    source_key = key_entry['key']
    source_idx = note_to_index(source_key)
    target_idx = note_to_index(target_key)
    semitones = target_idx - source_idx
    use_flats = should_use_flats(target_key)

    new_sections = []
    for section in key_entry.get('sections', []):
        new_chords = [
            transpose_chord(c, semitones, use_flats) if c.strip() else c
            for c in section.get('chords', [])
        ]
        new_sections.append({
            'label': section.get('label', ''),
            'rows': section.get('rows', 4),
            'endings': section.get('endings'),
            'chords': new_chords,
        })

    return {'key': target_key, 'sections': new_sections}


# --- Chord Input Parsing ---

def parse_chord_input(
    title: str,
    key: str,
    section_labels: str,
    chords_text: str,
    lyrics_text: Optional[str] = None
) -> Dict[str, Any]:
    """Parse modal/message input into the chord chart data model.

    Args:
        title: Song title.
        key: Key string (e.g. 'G').
        section_labels: Comma-separated section labels (e.g. 'Verse,Chorus').
        chords_text: Chord progression text. Sections separated by blank lines.
            Within a section, measures separated by '|', chords by spaces.
        lyrics_text: Optional lyrics text. Sections separated by blank lines.

    Returns:
        Dict matching the chord_charts data model (title, keys, lyrics).
    """
    labels = [s.strip() for s in section_labels.split(',') if s.strip()]
    chord_sections_raw = [
        block.strip() for block in chords_text.strip().split('\n\n') if block.strip()
    ]
    # If no blank-line separation, treat each line as a section
    if len(chord_sections_raw) == 1 and '\n' in chord_sections_raw[0]:
        chord_sections_raw = [
            line.strip() for line in chord_sections_raw[0].split('\n') if line.strip()
        ]

    sections = []
    for i, raw in enumerate(chord_sections_raw):
        label = labels[i] if i < len(labels) else f"Section {i + 1}"
        # Parse chords: split by | for measures, spaces for beats
        chords = []
        measures = [m.strip() for m in raw.replace('|', '\n').split('\n') if m.strip()]
        for measure in measures:
            measure_chords = [c.strip() for c in measure.split() if c.strip()]
            chords.extend(measure_chords)

        # Determine rows (how many beats per row for grid layout)
        rows = max(1, (len(chords) + 7) // 8)  # 8 chords per row as default

        sections.append({
            'label': label,
            'rows': rows,
            'endings': None,
            'chords': chords,
        })

    # Parse lyrics
    lyrics = None
    if lyrics_text and lyrics_text.strip():
        lyric_blocks = [
            block.strip() for block in lyrics_text.strip().split('\n\n') if block.strip()
        ]
        lyrics = []
        for i, block in enumerate(lyric_blocks):
            label = labels[i] if i < len(labels) else f"Section {i + 1}"
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            lyrics.append({'label': label, 'lines': lines})

    return {
        'title': title,
        'chart_title': title[:20] if len(title) > 20 else title,
        'keys': [{'key': key, 'sections': sections}],
        'lyrics': lyrics,
    }


# --- PDF Generation ---

# Grid cell dimensions
CELL_W = 28
CELL_H = 24
GRID_PAD = 4


def generate_chart_pdf(chart_data: Dict[str, Any]) -> io.BytesIO:
    """Generate a PDF chord chart matching the TNBGJ songbook format.

    Args:
        chart_data: Dict with title, chart_title, keys, lyrics.

    Returns:
        BytesIO buffer containing the PDF.
    """
    buf = io.BytesIO()
    page_w, page_h = landscape(letter)
    c = canvas.Canvas(buf, pagesize=landscape(letter))

    margin = 0.5 * inch
    usable_w = page_w - 2 * margin
    usable_h = page_h - 2 * margin

    # Split page: left panel (lyrics), right panel (chord grid)
    split_x = margin + usable_w * 0.4  # 40% lyrics, 60% chords

    title = chart_data.get('title', 'Untitled')
    chart_title = chart_data.get('chart_title', title)
    keys = chart_data.get('keys', [])
    lyrics = chart_data.get('lyrics')

    # --- Left Panel: Title + Lyrics ---
    _draw_lyrics_panel(c, margin, margin, split_x - margin - 10, usable_h, title, lyrics)

    # --- Right Panel: Chord Grid ---
    right_x = split_x + 10
    right_w = page_w - margin - right_x
    _draw_chord_panel(c, right_x, margin, right_w, usable_h, chart_title, keys)

    c.save()
    buf.seek(0)
    return buf


def _draw_lyrics_panel(
    c: canvas.Canvas,
    x: float, y: float, w: float, h: float,
    title: str, lyrics: Optional[List[Dict]]
):
    """Draw the left panel with title and lyrics."""
    top = y + h

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, top - 20, title)

    if not lyrics:
        return

    cursor_y = top - 50
    line_height = 14

    for section in lyrics:
        if cursor_y < y + 30:
            break
        # Section label
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, cursor_y, section.get('label', ''))
        cursor_y -= line_height + 2

        # Lines
        c.setFont("Helvetica", 10)
        for line in section.get('lines', []):
            if cursor_y < y + 10:
                break
            c.drawString(x + 10, cursor_y, line)
            cursor_y -= line_height

        cursor_y -= 8  # Gap between sections


def _draw_chord_panel(
    c: canvas.Canvas,
    x: float, y: float, w: float, h: float,
    chart_title: str, keys: List[Dict]
):
    """Draw the right panel with chart title and chord grids."""
    top = y + h

    # Chart title (italic)
    c.setFont("Helvetica-Oblique", 20)
    c.drawString(x, top - 24, chart_title)

    cursor_y = top - 50

    for key_entry in keys:
        if cursor_y < y + 50:
            break

        # "Key of X"
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x, cursor_y, f"Key of {key_entry['key']}")
        cursor_y -= 20

        for section in key_entry.get('sections', []):
            if cursor_y < y + 30:
                break

            chords = section.get('chords', [])
            label = section.get('label', '')
            cols = 8  # chords per row
            rows = max(1, (len(chords) + cols - 1) // cols)

            # Section label
            c.setFont("Helvetica-Bold", 9)
            c.drawString(x, cursor_y, label)
            cursor_y -= 4

            # Draw grid (column-major reading order for the TNBGJ format)
            grid_top = cursor_y
            for row in range(rows):
                for col in range(cols):
                    # Column-major index: read top to bottom, then next column
                    idx = col * rows + row
                    cell_x = x + col * CELL_W
                    cell_y = grid_top - (row + 1) * CELL_H

                    # Draw cell border
                    c.setStrokeColor(black)
                    c.setLineWidth(0.5)
                    c.rect(cell_x, cell_y, CELL_W, CELL_H)

                    # Draw chord text
                    if idx < len(chords):
                        chord = chords[idx]
                        c.setFont("Helvetica", 9)
                        c.drawCentredString(
                            cell_x + CELL_W / 2,
                            cell_y + CELL_H / 2 - 3,
                            chord
                        )

            cursor_y = grid_top - rows * CELL_H - 15

        cursor_y -= 10  # Gap between key groups
