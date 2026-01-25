"""Tests for LLM client chord chart generation."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError
from src.llm_client import (
    LLMClient,
    ChartGenerationRequest,
    ChartGenerationResponse,
    Section,
    LyricSection,
)


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "title": "Mountain Dew",
        "artist": "Traditional",
        "key": "G",
        "sections": [
            {
                "label": "Verse",
                "chords": ["G", "G", "C", "G", "D", "D", "G", "G"]
            },
            {
                "label": "Chorus",
                "chords": ["C", "C", "G", "G", "D", "D", "G", "G"]
            }
        ],
        "lyrics": [
            {
                "label": "Verse",
                "lines": ["Down the road here from me", "There's an old holler tree"]
            }
        ]
    }


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response (JSON in markdown)."""
    return '''```json
{
  "title": "Wildwood Flower",
  "artist": "Carter Family",
  "key": "C",
  "sections": [
    {
      "label": "Verse",
      "chords": ["C", "C", "F", "C", "G", "G", "C", "C"]
    }
  ]
}
```'''


class TestLLMClient:
    """Test suite for LLMClient."""

    def test_initialization_with_openai_key(self, monkeypatch):
        """Test LLMClient initializes with OpenAI API key."""
        monkeypatch.setenv('OPENAI_API_KEY', 'sk-test-key')
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)

        client = LLMClient()

        assert client.provider == 'openai'
        assert client.openai_api_key == 'sk-test-key'
        assert client.model == 'gpt-4'

    def test_initialization_with_anthropic_key(self, monkeypatch):
        """Test LLMClient initializes with Anthropic API key."""
        monkeypatch.delenv('OPENAI_API_KEY', raising=False)
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test-key')

        client = LLMClient()

        assert client.provider == 'anthropic'
        assert client.anthropic_api_key == 'sk-ant-test-key'
        assert client.model == 'claude-3-5-sonnet-20241022'

    def test_initialization_without_api_keys(self, monkeypatch):
        """Test LLMClient handles missing API keys gracefully."""
        monkeypatch.delenv('OPENAI_API_KEY', raising=False)
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)

        client = LLMClient()

        assert client.provider is None

    def test_generate_chord_chart_no_api_key(self, monkeypatch):
        """Test generate_chord_chart raises ValueError when no API key configured."""
        monkeypatch.delenv('OPENAI_API_KEY', raising=False)
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)

        client = LLMClient()

        with pytest.raises(ValueError, match="No LLM API key configured"):
            client.generate_chord_chart("Mountain Dew")

    def test_generate_chord_chart_with_openai(self, monkeypatch, mock_openai_response):
        """Test successful chart generation with OpenAI."""
        monkeypatch.setenv('OPENAI_API_KEY', 'sk-test-key')
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)

        with patch('openai.OpenAI') as mock_openai_class:
            # Mock OpenAI response
            import json
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.choices[0].message.content = json.dumps(mock_openai_response)
            mock_client.chat.completions.create.return_value = mock_response

            client = LLMClient()
            result = client.generate_chord_chart("Mountain Dew", "Traditional")

            assert isinstance(result, ChartGenerationResponse)
            assert result.title == "Mountain Dew"
            assert result.artist == "Traditional"
            assert result.key == "G"
            assert len(result.sections) == 2
            assert result.sections[0].label == "Verse"
            assert len(result.sections[0].chords) == 8

    def test_generate_chord_chart_with_anthropic(self, monkeypatch, mock_anthropic_response):
        """Test successful chart generation with Anthropic."""
        monkeypatch.delenv('OPENAI_API_KEY', raising=False)
        monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test-key')

        with patch('anthropic.Anthropic') as mock_anthropic_class:
            # Mock Anthropic response
            mock_client = MagicMock()
            mock_anthropic_class.return_value = mock_client
            mock_message = MagicMock()
            mock_content = MagicMock()
            mock_content.text = mock_anthropic_response
            mock_message.content = [mock_content]
            mock_client.messages.create.return_value = mock_message

            client = LLMClient()
            result = client.generate_chord_chart("Wildwood Flower", "Carter Family")

            assert isinstance(result, ChartGenerationResponse)
            assert result.title == "Wildwood Flower"
            assert result.artist == "Carter Family"
            assert result.key == "C"
            assert len(result.sections) == 1

    def test_generate_chord_chart_validation_error(self, monkeypatch):
        """Test that invalid LLM response raises ValidationError."""
        monkeypatch.setenv('OPENAI_API_KEY', 'sk-test-key')
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)

        with patch('openai.OpenAI') as mock_openai_class:
            # Mock invalid response (missing required 'key' field)
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.choices[0].message.content = '{"title": "Test", "sections": []}'
            mock_client.chat.completions.create.return_value = mock_response

            client = LLMClient()

            with pytest.raises(ValidationError):
                client.generate_chord_chart("Test Song")

    def test_generate_chord_chart_rate_limit_error(self, monkeypatch):
        """Test that OpenAI rate limit errors are handled."""
        monkeypatch.setenv('OPENAI_API_KEY', 'sk-test-key')
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)

        with patch('openai.OpenAI') as mock_openai_class:
            # Mock rate limit error
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client

            # Create a mock response for the exception
            mock_response = MagicMock()
            mock_response.request = MagicMock()

            # Import after patching
            import openai
            mock_client.chat.completions.create.side_effect = openai.RateLimitError(
                "Rate limit exceeded",
                response=mock_response,
                body=None
            )

            client = LLMClient()

            with pytest.raises(Exception, match="rate limited"):
                client.generate_chord_chart("Test Song")

    def test_chart_generation_request_validation(self):
        """Test ChartGenerationRequest Pydantic validation."""
        # Valid request
        request = ChartGenerationRequest(song_title="Mountain Dew", artist="Traditional")
        assert request.song_title == "Mountain Dew"
        assert request.artist == "Traditional"

        # Request without artist (optional)
        request = ChartGenerationRequest(song_title="Mountain Dew")
        assert request.song_title == "Mountain Dew"
        assert request.artist is None

    def test_chart_generation_response_validation(self):
        """Test ChartGenerationResponse Pydantic validation."""
        # Valid response
        response_data = {
            "title": "Mountain Dew",
            "artist": "Traditional",
            "key": "G",
            "sections": [
                {
                    "label": "Verse",
                    "chords": ["G", "C", "D", "G"]
                }
            ]
        }
        response = ChartGenerationResponse.model_validate(response_data)
        assert response.title == "Mountain Dew"
        assert response.key == "G"
        assert len(response.sections) == 1

        # Invalid response (missing key)
        invalid_data = {
            "title": "Test",
            "sections": []
        }
        with pytest.raises(ValidationError):
            ChartGenerationResponse.model_validate(invalid_data)

    def test_section_validation(self):
        """Test Section Pydantic validation."""
        section = Section(label="Verse", chords=["G", "C", "D", "G"])
        assert section.label == "Verse"
        assert len(section.chords) == 4

    def test_lyric_section_validation(self):
        """Test LyricSection Pydantic validation."""
        lyric_section = LyricSection(
            label="Verse",
            lines=["Line 1", "Line 2", "Line 3"]
        )
        assert lyric_section.label == "Verse"
        assert len(lyric_section.lines) == 3
