"""Tests for LLM prompt rendering and validation."""
import pytest
import json
import tiktoken
from src.llm_prompt import (
    render_prompt,
    FEW_SHOT_EXAMPLES,
    ChordChartSchema,
    SYSTEM_PROMPT
)


def test_render_prompt_token_count():
    """Verify rendered prompt is under 2000 tokens"""
    prompt = render_prompt("Mountain Dew", "Traditional")
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(prompt)
    assert len(tokens) < 2000, f"Prompt too long: {len(tokens)} tokens"


def test_few_shot_examples_valid_json():
    """All few-shot examples parse as valid JSON"""
    for example in FEW_SHOT_EXAMPLES:
        chart_json = json.loads(example['assistant'])
        # Validate against Pydantic schema
        chart = ChordChartSchema(**chart_json)
        assert chart.title
        assert len(chart.keys) > 0


def test_template_interpolation():
    """Template correctly inserts song title and artist"""
    prompt = render_prompt("Test Song", "Test Artist")
    assert "Test Song" in prompt
    assert "Test Artist" in prompt
    assert SYSTEM_PROMPT in prompt
    assert len([e for e in FEW_SHOT_EXAMPLES]) >= 3  # At least 3 examples


def test_schema_matches_database_structure():
    """Pydantic schema matches database.py chord_charts table"""
    # Test with example data matching database fields: title, chart_title, keys, lyrics
    chart_data = {
        "title": "Test",
        "chart_title": "Test Chart",
        "keys": [{
            "key": "G",
            "sections": [{
                "label": "Verse",
                "rows": 8,
                "chords": ["G", "C", "D", "G"] * 8
            }]
        }],
        "lyrics": [{"label": "Verse", "lines": ["Test line"]}]
    }
    chart = ChordChartSchema(**chart_data)

    # Verify serialization matches database JSON format
    db_json = chart.model_dump(mode='json')
    assert 'title' in db_json
    assert 'chart_title' in db_json
    assert 'keys' in db_json
    assert 'lyrics' in db_json
    assert isinstance(db_json['keys'], list)

    # Verify no artist or chord_progression fields (those don't exist in database)
    assert 'artist' not in db_json
    assert 'chord_progression' not in db_json


def test_examples_cover_diversity():
    """Few-shot examples include vocal, instrumental, unusual key"""
    examples_json = [json.loads(e['assistant']) for e in FEW_SHOT_EXAMPLES]

    has_vocal = any(e.get('lyrics') for e in examples_json)
    has_instrumental = any(e.get('lyrics') is None for e in examples_json)

    all_keys = [e['keys'][0]['key'] for e in examples_json]
    has_unusual_key = any(k in ['Bb', 'Eb', 'F#', 'Ab'] for k in all_keys)

    assert has_vocal, "Must include vocal song with lyrics"
    assert has_instrumental, "Must include instrumental fiddle tune"
    assert has_unusual_key, "Must include unusual key example"
