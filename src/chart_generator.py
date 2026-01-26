"""Chord chart PDF generation and transposition for Jambot.

Generates landscape letter PDFs matching the TNBGJ songbook format:
- Left panel: title + lyrics
- Right panel: chord grid (column-major reading order)
"""
import io
from typing import Dict, List, Optional, Any

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import black, HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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

        # Standard grid is 8 rows tall; columns expand as needed
        rows = 8 if len(chords) > 8 else max(1, len(chords))

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

import math
import os

# Grid cell dimensions (matches TNBGJ songbook format)
CELL_W = 28
CELL_H = 24
SECTION_GAP = 8  # gap between sections (in points)

# Font names (serif to match Georgia in the songbook)
FONT_REGULAR = 'Times-Roman'
FONT_BOLD = 'Times-Bold'
FONT_ITALIC = 'Times-Italic'
FONT_BOLD_ITALIC = 'Times-BoldItalic'

# Try to register Georgia if available on the system
_fonts_initialized = False


def _init_fonts():
    """Register Georgia fonts if available, otherwise use Times-Roman."""
    global _fonts_initialized, FONT_REGULAR, FONT_BOLD, FONT_ITALIC, FONT_BOLD_ITALIC
    if _fonts_initialized:
        return
    _fonts_initialized = True

    georgia_paths = {
        'Georgia': [
            '/Library/Fonts/Georgia.ttf',
            '/System/Library/Fonts/Supplemental/Georgia.ttf',
            '/usr/share/fonts/truetype/msttcorefonts/Georgia.ttf',
        ],
        'Georgia-Bold': [
            '/Library/Fonts/Georgia Bold.ttf',
            '/System/Library/Fonts/Supplemental/Georgia Bold.ttf',
            '/usr/share/fonts/truetype/msttcorefonts/Georgia_Bold.ttf',
        ],
        'Georgia-Italic': [
            '/Library/Fonts/Georgia Italic.ttf',
            '/System/Library/Fonts/Supplemental/Georgia Italic.ttf',
            '/usr/share/fonts/truetype/msttcorefonts/Georgia_Italic.ttf',
        ],
        'Georgia-BoldItalic': [
            '/Library/Fonts/Georgia Bold Italic.ttf',
            '/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf',
            '/usr/share/fonts/truetype/msttcorefonts/Georgia_Bold_Italic.ttf',
        ],
    }

    registered = {}
    for font_name, paths in georgia_paths.items():
        for path in paths:
            if os.path.exists(path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, path))
                    registered[font_name] = True
                    break
                except Exception:
                    pass

    if 'Georgia' in registered:
        FONT_REGULAR = 'Georgia'
        FONT_BOLD = registered.get('Georgia-Bold') and 'Georgia-Bold' or 'Georgia'
        FONT_ITALIC = registered.get('Georgia-Italic') and 'Georgia-Italic' or 'Georgia'
        FONT_BOLD_ITALIC = registered.get('Georgia-BoldItalic') and 'Georgia-BoldItalic' or 'Georgia'


def generate_chart_pdf(chart_data: Dict[str, Any]) -> io.BytesIO:
    """Generate a PDF chord chart matching the TNBGJ songbook format.

    Landscape letter page with two panels:
    - Left: title + lyrics (serif font)
    - Right: chart title (bold italic) + "Key of X" + chord grid
      (vertical lines only, column-major reading order)

    Args:
        chart_data: Dict with title, chart_title, keys, lyrics, status (optional).

    Returns:
        BytesIO buffer containing the PDF.
    """
    _init_fonts()

    buf = io.BytesIO()
    page_w, page_h = landscape(letter)
    c = canvas.Canvas(buf, pagesize=landscape(letter))

    margin = 0.5 * inch
    usable_w = page_w - 2 * margin
    usable_h = page_h - 2 * margin

    # Equal-width panels with gap (matches CSS flex: 1 + gap: 0.4in)
    gap = 0.4 * inch
    panel_w = (usable_w - gap) / 2

    title = chart_data.get('title', 'Untitled')
    chart_title = chart_data.get('chart_title', title)
    keys = chart_data.get('keys', [])
    lyrics = chart_data.get('lyrics')
    status = chart_data.get('status', 'draft')

    # --- Left Panel: Title + Lyrics ---
    _draw_lyrics_panel(c, margin, margin, panel_w, usable_h, title, lyrics)

    # --- Panel Divider (subtle gray line) ---
    divider_x = margin + panel_w + gap * 0.3
    c.setStrokeColor(HexColor('#cccccc'))
    c.setLineWidth(0.5)
    c.line(divider_x, margin, divider_x, margin + usable_h)

    # --- Right Panel: Chord Grid ---
    chord_x = margin + panel_w + gap
    _draw_chord_panel(c, chord_x, margin, panel_w, usable_h, chart_title, keys)

    # --- Draft Footer (if draft status) ---
    if status == 'draft':
        c.setFillGray(0.5)
        c.setFont("Helvetica-Bold", 12)
        footer_y = margin * 0.3
        c.drawCentredString(page_w / 2, footer_y, "DRAFT")

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

    # Title (Georgia/Times Bold 18pt)
    c.setFont(FONT_BOLD, 18)
    c.drawString(x, top - 22, title)

    if not lyrics:
        return

    # Handle case where lyrics is a string (from AI) instead of list
    if isinstance(lyrics, str):
        return  # Skip string lyrics, PDF expects list format

    cursor_y = top - 50
    line_height = 15.4  # 11pt * 1.4 line-height

    for section in lyrics:
        if cursor_y < y + 30:
            break
        # Section label (bold italic)
        label = section.get('label', '')
        if label:
            c.setFont(FONT_BOLD_ITALIC, 11)
            c.drawString(x, cursor_y, label)
            cursor_y -= line_height

        # Lyric lines
        c.setFont(FONT_REGULAR, 11)
        for line in section.get('lines', []):
            if cursor_y < y + 10:
                break
            c.drawString(x, cursor_y, line)
            cursor_y -= line_height

        cursor_y -= 10  # Gap between lyric sections


def _draw_chord_panel(
    c: canvas.Canvas,
    x: float, y: float, w: float, h: float,
    chart_title: str, keys: List[Dict]
):
    """Draw the right panel with chart title and chord grids.

    Layout matches the TNBGJ songbook:
    - Chart title centered, bold italic 22pt
    - Key groups placed side by side (multi-key songs)
    - Within each key group: "Key of X" centered, sections side by side
    - Grid uses only vertical lines between columns
    - Column-major reading order (top-to-bottom, left-to-right)
    """
    top = y + h
    KEY_GROUP_GAP = 14  # gap between key groups (0.1in ~ 7pt, using 14 for clarity)

    # Chart title (bold italic, 22pt, centered)
    c.setFont(FONT_BOLD_ITALIC, 22)
    title_w = c.stringWidth(chart_title, FONT_BOLD_ITALIC, 22)
    c.drawString(x + (w - title_w) / 2, top - 26, chart_title)

    # Pre-calculate key group widths for horizontal layout
    key_group_infos = []
    for key_entry in keys:
        sections = key_entry.get('sections', [])
        section_infos = []
        for section in sections:
            rows = section.get('rows', 8)
            chords = section.get('chords', [])
            cols = max(1, math.ceil(len(chords) / rows))
            section_infos.append({
                'section': section,
                'rows': rows,
                'cols': cols,
                'width': cols * CELL_W,
            })
        group_width = sum(s['width'] for s in section_infos) + \
            max(0, len(section_infos) - 1) * SECTION_GAP
        # Ensure group is wide enough for the "Key of X" label
        c.setFont(FONT_BOLD, 14)
        key_label_w = c.stringWidth(f"Key of {key_entry['key']}", FONT_BOLD, 14)
        group_width = max(group_width, key_label_w)
        key_group_infos.append({
            'key_entry': key_entry,
            'section_infos': section_infos,
            'width': group_width,
        })

    if not key_group_infos:
        return

    # Total width of all key groups side by side
    total_groups_width = sum(g['width'] for g in key_group_infos) + \
        max(0, len(key_group_infos) - 1) * KEY_GROUP_GAP

    # Center all key groups horizontally
    groups_start_x = x + (w - total_groups_width) / 2
    body_top = top - 44  # below chart title

    group_x = groups_start_x
    for group_info in key_group_infos:
        key_entry = group_info['key_entry']
        section_infos = group_info['section_infos']
        group_w = group_info['width']

        # "Key of X" (bold 14pt, centered within this group)
        c.setFont(FONT_BOLD, 14)
        key_text = f"Key of {key_entry['key']}"
        key_w = c.stringWidth(key_text, FONT_BOLD, 14)
        c.drawString(group_x + (group_w - key_w) / 2, body_top, key_text)

        # Sections start below the key label
        sections_top = body_top - 22

        # Center sections within this key group
        sections_width = sum(s['width'] for s in section_infos) + \
            max(0, len(section_infos) - 1) * SECTION_GAP
        section_x = group_x + (group_w - sections_width) / 2

        for info in section_infos:
            section = info['section']
            rows = info['rows']
            cols = info['cols']
            chords = section.get('chords', [])
            label = section.get('label', '')
            endings = section.get('endings')

            # Section label (centered above section)
            label_y = sections_top
            if label:
                c.setFont(FONT_BOLD, 9)
                c.setFillColor(black)
                label_w = c.stringWidth(label, FONT_BOLD, 9)
                c.drawString(section_x + (info['width'] - label_w) / 2, label_y, label)

            # Ending markers below label, above grid columns
            if endings:
                marker_row_y = label_y - 14
                _draw_ending_markers(c, section_x, marker_row_y, endings)

            # Grid starts below header area
            header_space = 16 + (14 if endings else 0)
            grid_top = label_y - header_space

            # Draw vertical lines only (no horizontal lines)
            c.setStrokeColor(black)
            c.setLineWidth(0.75)
            grid_bottom = grid_top - rows * CELL_H
            for col in range(cols + 1):
                line_x = section_x + col * CELL_W
                c.line(line_x, grid_top, line_x, grid_bottom)

            # Draw chord text (column-major order)
            c.setFont(FONT_BOLD, 11)
            c.setFillColor(black)
            for col in range(cols):
                for row in range(rows):
                    idx = col * rows + row
                    if idx < len(chords):
                        chord = chords[idx]
                        cx = section_x + col * CELL_W + CELL_W / 2
                        cy = grid_top - row * CELL_H - CELL_H / 2 - 3
                        c.drawCentredString(cx, cy, chord)

            section_x += info['width'] + SECTION_GAP

        group_x += group_w + KEY_GROUP_GAP


def _draw_ending_markers(
    c: canvas.Canvas,
    section_x: float, y: float,
    endings: List[Dict]
):
    """Draw circled ending numbers above their respective columns."""
    for ending_info in endings:
        col = ending_info.get('column', 0)
        ending_num = str(ending_info.get('ending', ''))

        # Center the marker above the column
        marker_x = section_x + col * CELL_W + CELL_W / 2

        # Draw circle (radius 6pt)
        c.setStrokeColor(black)
        c.setFillColor(black)
        c.setLineWidth(0.5)
        c.circle(marker_x, y + 4, 6, stroke=1, fill=0)

        # Draw number inside circle
        c.setFont(FONT_BOLD, 7)
        c.setFillColor(black)
        num_w = c.stringWidth(ending_num, FONT_BOLD, 7)
        c.drawString(marker_x - num_w / 2, y + 1.5, ending_num)
