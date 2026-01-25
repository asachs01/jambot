"""LLM system prompt and few-shot examples for TNBGJ bluegrass chord chart generation."""
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from jinja2 import Template


class ChordSection(BaseModel):
    """Chord section with grid layout."""
    label: str  # 'Verse', 'Chorus', 'A Part', 'B Part'
    rows: int = 8  # Grid height (default 8 for standard TNBGJ format)
    endings: Optional[List[Dict[str, Any]]] = None
    chords: List[str]  # Chord progression in column-major order


class KeyEntry(BaseModel):
    """Key entry with sections."""
    key: str  # 'G', 'C', 'D', 'A', etc.
    sections: List[ChordSection]


class LyricSection(BaseModel):
    """Lyric section."""
    label: str
    lines: List[str]


class ChordChartSchema(BaseModel):
    """Schema matching database chord_charts table structure."""
    title: str
    chart_title: Optional[str] = None  # Abbreviated title for chart header
    keys: List[KeyEntry]
    lyrics: Optional[List[LyricSection]] = None


SYSTEM_PROMPT = '''You are a bluegrass chord chart generator following The North Bay Bluegrass Jammers (TNBGJ) songbook format.

OUTPUT FORMAT:
- Return ONLY valid JSON matching this structure:
  {
    "title": "Song Title",
    "chart_title": "Abbreviated Title",
    "keys": [
      {
        "key": "G",
        "sections": [
          {
            "label": "Verse" | "Chorus" | "A Part" | "B Part",
            "rows": 8,
            "chords": ["G", "G", "C", "G", "D", "D", "G", "G", ...]
          }
        ]
      }
    ],
    "lyrics": [
      {"label": "Verse", "lines": ["Line 1", "Line 2", ...]}
    ]
  }

CHORD GRID RULES:
- 4-column grid layout (column-major reading: top-to-bottom, left-to-right)
- 8 rows tall by default (32 beats total for standard sections)
- Chords array fills columns: [col1row1, col1row2, ..., col2row1, col2row2, ...]
- Empty cells represented as empty strings ""

SECTION TYPES:
- Vocal songs: "Verse", "Chorus", "Bridge"
- Fiddle tunes: "A Part", "B Part", "C Part"

BLUEGRASS KEYS:
- Prefer: G, C, D, A (90% of bluegrass repertoire)
- Occasional: E, F, Bb, F# (for specific songs)

LYRICS:
- Include for vocal songs, omit for instrumentals
- Section labels must match chord sections

CHART_TITLE:
- Optional abbreviated title for chart header (shorter than full title if needed)'''


FEW_SHOT_EXAMPLES = [
    {
        "user": "Generate chord chart for 'Will the Circle Be Unbroken' by Traditional",
        "assistant": json.dumps({
            "title": "Will the Circle Be Unbroken",
            "chart_title": "Circle Unbroken",
            "keys": [{
                "key": "G",
                "sections": [{
                    "label": "Verse",
                    "rows": 8,
                    "chords": ["G", "G", "C", "G", "D", "D", "G", "G"] * 4
                }, {
                    "label": "Chorus",
                    "rows": 8,
                    "chords": ["G", "G", "C", "G", "G", "G", "D", "D",
                               "G", "G", "C", "G", "D", "D", "G", "G"] * 2
                }]
            }],
            "lyrics": [
                {"label": "Verse", "lines": ["I was standing by the window"]},
                {"label": "Chorus", "lines": ["Will the circle be unbroken"]}
            ]
        })
    },
    {
        "user": "Generate chord chart for 'Soldier's Joy' by Traditional",
        "assistant": json.dumps({
            "title": "Soldier's Joy",
            "chart_title": "Soldier's Joy",
            "keys": [{
                "key": "D",
                "sections": [{
                    "label": "A Part",
                    "rows": 8,
                    "chords": ["D"] * 16 + ["A"] * 8 + ["D"] * 8
                }, {
                    "label": "B Part",
                    "rows": 8,
                    "chords": ["D", "D", "G", "G", "A", "A", "D", "D"] * 4
                }]
            }],
            "lyrics": None
        })
    },
    {
        "user": "Generate chord chart for 'Man of Constant Sorrow' by Traditional",
        "assistant": json.dumps({
            "title": "Man of Constant Sorrow",
            "chart_title": "Constant Sorrow",
            "keys": [{
                "key": "Bb",
                "sections": [{
                    "label": "Verse",
                    "rows": 8,
                    "chords": ["Bb", "Bb", "Eb", "Bb", "F", "F", "Bb", "Bb"] * 4
                }]
            }],
            "lyrics": [{"label": "Verse", "lines": ["I am a man of constant sorrow"]}]
        })
    }
]


PROMPT_TEMPLATE = Template('''{{ system_prompt }}

EXAMPLES:
{% for example in examples %}
User: {{ example.user }}
Assistant: {{ example.assistant }}

{% endfor %}
USER REQUEST:
Generate chord chart for "{{ song_title }}" by {{ artist }}

Return ONLY valid JSON following the schema above.''')


def render_prompt(song_title: str, artist: str) -> str:
    """Render LLM prompt with dynamic song/artist insertion.

    Args:
        song_title: Song title to generate chart for
        artist: Artist name

    Returns:
        Formatted prompt string with system instructions + examples + query
    """
    return PROMPT_TEMPLATE.render(
        system_prompt=SYSTEM_PROMPT,
        examples=FEW_SHOT_EXAMPLES,
        song_title=song_title,
        artist=artist
    )
