"""Tests for LLM-powered intent parser."""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from src.intent_parser import (
    parse_mention_intent,
    Intent,
    IntentResult
)


class TestIntentParser:
    """Test cases for intent parsing functionality."""

    @pytest.fixture
    def mock_openrouter_response(self):
        """Fixture to create mock OpenRouter API responses."""
        def _create_response(intent_data):
            return {
                "choices": [{
                    "message": {
                        "content": str(intent_data).replace("'", '"')
                    }
                }]
            }
        return _create_response

    @pytest.mark.asyncio
    async def test_view_intent_simple(self, mock_openrouter_response):
        """Test parsing simple VIEW intent."""
        mock_response = mock_openrouter_response({
            "intent": "view",
            "song_title": "Wagon Wheel",
            "artist": None,
            "key": None,
            "target_key": None,
            "confidence": 0.95
        })

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response
            ))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent("do you have chords to Wagon Wheel?")

            assert result is not None
            assert result.intent == Intent.VIEW
            assert result.song_title == "Wagon Wheel"
            assert result.artist is None
            assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_view_intent_with_key(self, mock_openrouter_response):
        """Test VIEW intent with requested key."""
        mock_response = mock_openrouter_response({
            "intent": "view",
            "song_title": "Rocky Top",
            "artist": None,
            "key": "D",
            "target_key": None,
            "confidence": 0.92
        })

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response
            ))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent("show me Rocky Top in the key of D")

            assert result is not None
            assert result.intent == Intent.VIEW
            assert result.song_title == "Rocky Top"
            assert result.key == "D"

    @pytest.mark.asyncio
    async def test_generate_intent_with_artist(self, mock_openrouter_response):
        """Test GENERATE intent with artist."""
        mock_response = mock_openrouter_response({
            "intent": "generate",
            "song_title": "Mountain Dew",
            "artist": "Grandpa Jones",
            "key": None,
            "target_key": None,
            "confidence": 0.88
        })

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response
            ))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent(
                "generate a chord chart for Mountain Dew by Grandpa Jones"
            )

            assert result is not None
            assert result.intent == Intent.GENERATE
            assert result.song_title == "Mountain Dew"
            assert result.artist == "Grandpa Jones"

    @pytest.mark.asyncio
    async def test_create_intent(self, mock_openrouter_response):
        """Test CREATE intent."""
        mock_response = mock_openrouter_response({
            "intent": "create",
            "song_title": None,
            "artist": None,
            "key": None,
            "target_key": None,
            "confidence": 0.98
        })

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response
            ))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent("create a new chart")

            assert result is not None
            assert result.intent == Intent.CREATE
            assert result.song_title is None

    @pytest.mark.asyncio
    async def test_transpose_intent(self, mock_openrouter_response):
        """Test TRANSPOSE intent."""
        mock_response = mock_openrouter_response({
            "intent": "transpose",
            "song_title": "Foggy Mountain Breakdown",
            "artist": None,
            "key": None,
            "target_key": "G",
            "confidence": 0.93
        })

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response
            ))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent(
                "transpose Foggy Mountain Breakdown to key of G"
            )

            assert result is not None
            assert result.intent == Intent.TRANSPOSE
            assert result.song_title == "Foggy Mountain Breakdown"
            assert result.target_key == "G"

    @pytest.mark.asyncio
    async def test_list_intent(self, mock_openrouter_response):
        """Test LIST intent."""
        mock_response = mock_openrouter_response({
            "intent": "list",
            "song_title": None,
            "artist": None,
            "key": None,
            "target_key": None,
            "confidence": 1.0
        })

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response
            ))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent("list all the charts you have")

            assert result is not None
            assert result.intent == Intent.LIST
            assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_search_by_artist(self, mock_openrouter_response):
        """Test SEARCH intent with artist."""
        mock_response = mock_openrouter_response({
            "intent": "search",
            "song_title": None,
            "artist": "Bill Monroe",
            "key": None,
            "target_key": None,
            "confidence": 0.87
        })

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response
            ))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent("do you have any Bill Monroe songs?")

            assert result is not None
            assert result.intent == Intent.SEARCH
            assert result.artist == "Bill Monroe"

    @pytest.mark.asyncio
    async def test_search_by_partial_title(self, mock_openrouter_response):
        """Test SEARCH intent with partial song title."""
        mock_response = mock_openrouter_response({
            "intent": "search",
            "song_title": "bluegrass",
            "artist": None,
            "key": None,
            "target_key": None,
            "confidence": 0.75
        })

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response
            ))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent("show me bluegrass classics")

            assert result is not None
            assert result.intent == Intent.SEARCH
            assert result.song_title == "bluegrass"

    @pytest.mark.asyncio
    async def test_delete_intent(self, mock_openrouter_response):
        """Test DELETE intent."""
        mock_response = mock_openrouter_response({
            "intent": "delete",
            "song_title": "Old Song",
            "artist": None,
            "key": None,
            "target_key": None,
            "confidence": 0.9
        })

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response
            ))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent("delete the chart for Old Song")

            assert result is not None
            assert result.intent == Intent.DELETE
            assert result.song_title == "Old Song"

    @pytest.mark.asyncio
    async def test_unknown_intent(self, mock_openrouter_response):
        """Test UNKNOWN intent for off-topic messages."""
        mock_response = mock_openrouter_response({
            "intent": "unknown",
            "song_title": None,
            "artist": None,
            "key": None,
            "target_key": None,
            "confidence": 1.0
        })

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response
            ))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent("what's the weather like today?")

            assert result is not None
            assert result.intent == Intent.UNKNOWN

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        """Test that timeout returns None for fallback."""
        with patch('httpx.AsyncClient') as mock_client:
            # Simulate timeout
            mock_post = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent(
                "do you have Wagon Wheel?",
                timeout=0.1
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self):
        """Test that API errors return None for fallback."""
        with patch('httpx.AsyncClient') as mock_client:
            # Simulate HTTP error
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPError("API Error")
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent("show me charts")

            assert result is None

    @pytest.mark.asyncio
    async def test_invalid_json_returns_none(self, mock_openrouter_response):
        """Test that invalid JSON response returns None for fallback."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(
                status_code=200,
                json=lambda: {"choices": [{"message": {"content": "not valid json{{"}}]}
            ))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent("show me charts")

            assert result is None

    @pytest.mark.asyncio
    async def test_missing_required_fields_returns_none(self, mock_openrouter_response):
        """Test that response missing required fields returns None."""
        mock_response = mock_openrouter_response({
            "song_title": "Some Song"
            # Missing intent and confidence
        })

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock(return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response
            ))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await parse_mention_intent("show me charts")

            assert result is None

    @pytest.mark.asyncio
    async def test_empty_message_returns_none(self):
        """Test that empty message returns None."""
        result = await parse_mention_intent("")
        assert result is None

        result = await parse_mention_intent("   ")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_api_key_returns_none(self):
        """Test that missing API key returns None."""
        with patch('src.intent_parser.Config.OPENROUTER_API_KEY', None):
            result = await parse_mention_intent("show me charts")
            assert result is None
