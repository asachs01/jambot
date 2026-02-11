"""LLM-powered intent parser for natural language @mention handling.

This module provides intent parsing capabilities for Discord @mentions,
allowing users to interact with JamBot using natural language instead of
rigid command patterns.
"""
import json
import asyncio
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import httpx

from src.logger import logger
from src.config import Config


class Intent(Enum):
    """Possible intents from @mention messages."""
    VIEW = "view"
    CREATE = "create"
    GENERATE = "generate"
    TRANSPOSE = "transpose"
    DELETE = "delete"
    LIST = "list"
    SEARCH = "search"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Result of intent parsing."""
    intent: Intent
    song_title: Optional[str] = None
    artist: Optional[str] = None
    key: Optional[str] = None
    target_key: Optional[str] = None
    confidence: float = 0.0


# System prompt for intent classification
INTENT_SYSTEM_PROMPT = """You are an intent classifier for a Discord bot that manages bluegrass jam chord charts.

Your job is to parse natural language messages and identify what the user wants to do.

Valid intents:
- VIEW: User wants to see/get an existing chord chart (e.g., "show me Wagon Wheel", "chords for Mountain Dew", "do you have Rocky Top?")
- CREATE: User wants to manually create a new chart via a form (e.g., "create a chart", "add a new song", "I want to make a chart")
- GENERATE: User wants AI to generate a chart from a song title (e.g., "generate chords for Wagon Wheel", "create chart for Rocky Top in G")
- TRANSPOSE: User wants to change the key of an existing chart (e.g., "transpose Wagon Wheel to D", "change Rocky Top to key of A")
- DELETE: User wants to delete a chart (e.g., "delete Wagon Wheel", "remove the chart for Rocky Top")
- LIST: User wants to see all available charts (e.g., "list all charts", "what songs do you have?", "show me all the charts")
- SEARCH: User wants to find charts by artist or partial title (e.g., "do you have any Willie Nelson songs?", "show me bluegrass classics")
- UNKNOWN: Cannot determine intent or message is not related to chord charts

Extract these fields if present:
- song_title: The name of the song (without "by Artist" part)
- artist: The artist name (if mentioned)
- key: The musical key (for GENERATE intent - e.g., G, A, D, C)
- target_key: The target key (for TRANSPOSE intent)
- confidence: 0.0 to 1.0 indicating how confident you are in the classification

Return ONLY valid JSON in this exact format:
{
  "intent": "view",
  "song_title": "Wagon Wheel",
  "artist": "Old Crow Medicine Show",
  "key": null,
  "target_key": null,
  "confidence": 0.95
}

Examples:
- "hey jambot do you have chords to Wagon Wheel?" → VIEW with song_title="Wagon Wheel", confidence=0.9
- "show me Rocky Top in the key of D" → VIEW with song_title="Rocky Top", key="D", confidence=0.95
- "generate a chord chart for Mountain Dew by Grandpa Jones" → GENERATE with song_title="Mountain Dew", artist="Grandpa Jones", confidence=0.9
- "create a new chart" → CREATE with confidence=0.95
- "transpose Foggy Mountain Breakdown to key of G" → TRANSPOSE with song_title="Foggy Mountain Breakdown", target_key="G", confidence=0.95
- "do you have any Bill Monroe songs?" → SEARCH with artist="Bill Monroe", confidence=0.85
- "list all the charts you have" → LIST with confidence=1.0
- "what's the weather like?" → UNKNOWN with confidence=1.0

Be strict: only return high confidence (>0.7) if you're sure. Return UNKNOWN for ambiguous or off-topic messages."""


async def parse_mention_intent(
    message_text: str,
    model: Optional[str] = None,
    timeout: float = 5.0
) -> Optional[IntentResult]:
    """Parse user intent from a natural language @mention message.

    Uses OpenRouter API with a fast, cheap model to classify the intent
    and extract relevant parameters.

    Args:
        message_text: The message text with @mention already stripped.
        model: OpenRouter model to use. Defaults to Config.INTENT_MODEL.
        timeout: Request timeout in seconds. Defaults to 5.0.

    Returns:
        IntentResult if parsing succeeds, None if any error occurs
        (timeout, API error, parse error, etc.) so caller can fall back
        to regex patterns.
    """
    if not message_text or not message_text.strip():
        return None

    # Get API key and model from config
    api_key = Config.OPENROUTER_API_KEY
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not configured - intent parsing disabled")
        return None

    model = model or Config.INTENT_MODEL

    # Build OpenRouter API request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://jambot.app",
        "X-Title": "JamBot Intent Parser"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": message_text}
        ],
        "temperature": 0.1,  # Low temperature for consistent classification
        "max_tokens": 200,   # Small response expected
    }

    try:
        # Make API call with timeout
        async with httpx.AsyncClient() as client:
            response = await asyncio.wait_for(
                client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers
                ),
                timeout=timeout
            )

            response.raise_for_status()
            data = response.json()

            # Extract response content
            if not data.get("choices") or len(data["choices"]) == 0:
                logger.warning("OpenRouter returned no choices")
                return None

            content = data["choices"][0]["message"]["content"].strip()

            # Parse JSON response
            result_data = json.loads(content)

            # Validate required fields
            if "intent" not in result_data or "confidence" not in result_data:
                logger.warning(f"Invalid intent response format: {result_data}")
                return None

            # Parse intent enum
            intent_str = result_data["intent"].lower()
            try:
                intent = Intent(intent_str)
            except ValueError:
                logger.warning(f"Unknown intent value: {intent_str}")
                return None

            # Build IntentResult
            return IntentResult(
                intent=intent,
                song_title=result_data.get("song_title"),
                artist=result_data.get("artist"),
                key=result_data.get("key"),
                target_key=result_data.get("target_key"),
                confidence=float(result_data["confidence"])
            )

    except asyncio.TimeoutError:
        logger.warning(f"Intent parsing timed out after {timeout}s")
        return None
    except httpx.HTTPError as e:
        logger.warning(f"OpenRouter API error: {e}")
        return None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning(f"Failed to parse intent response: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in intent parsing: {e}", exc_info=True)
        return None
