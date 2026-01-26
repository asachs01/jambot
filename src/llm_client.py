"""LLM client for AI-powered chord chart generation."""
import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ValidationError
from src.logger import logger


class Section(BaseModel):
    """A section of a chord chart (e.g., Verse, Chorus)."""
    label: str = Field(..., description="Section label (e.g., 'Verse', 'Chorus', 'A Part')")
    chords: List[str] = Field(..., description="List of chords in this section")


class LyricSection(BaseModel):
    """A section of lyrics."""
    label: str = Field(..., description="Section label matching chord section")
    lines: List[str] = Field(..., description="Lyric lines for this section")


class ChartGenerationRequest(BaseModel):
    """Request for generating a chord chart."""
    song_title: str = Field(..., description="Title of the song")
    artist: Optional[str] = Field(None, description="Artist or composer name")


class ChartGenerationResponse(BaseModel):
    """Response from LLM chord chart generation."""
    title: str = Field(..., description="Song title")
    artist: Optional[str] = Field(None, description="Artist or composer")
    key: str = Field(..., description="Musical key (e.g., 'G', 'C', 'D')")
    sections: List[Section] = Field(..., description="Chart sections with chord progressions")
    lyrics: Optional[List[LyricSection]] = Field(None, description="Optional lyrics sections")


class LLMClient:
    """Client for LLM-powered chord chart generation using OpenAI or Anthropic."""

    def __init__(self):
        """Initialize LLM client with API credentials from environment."""
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.model = os.getenv('LLM_MODEL', 'gpt-4')

        if not self.openai_api_key and not self.anthropic_api_key:
            logger.warning(
                "No LLM API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY "
                "environment variable to enable AI chord chart generation."
            )

        # Determine which provider to use
        self.provider = None
        if self.anthropic_api_key:
            self.provider = 'anthropic'
            self.model = os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')
        elif self.openai_api_key:
            self.provider = 'openai'
            self.model = os.getenv('LLM_MODEL', 'gpt-4')

    def generate_chord_chart(
        self,
        song_title: str,
        artist: Optional[str] = None
    ) -> ChartGenerationResponse:
        """Generate a chord chart using LLM.

        Args:
            song_title: Title of the song.
            artist: Optional artist/composer name.

        Returns:
            ChartGenerationResponse with generated chart data.

        Raises:
            ValueError: If no API key is configured.
            ValidationError: If LLM response doesn't match expected schema.
            Exception: For API errors or rate limits.
        """
        if not self.provider:
            raise ValueError(
                "No LLM API key configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY"
            )

        # Construct prompt
        artist_part = f" by {artist}" if artist else ""
        prompt = f"""Generate a chord chart for the song "{song_title}"{artist_part}.

Return a JSON object with this exact structure:
{{
  "title": "{song_title}",
  "artist": "{artist or 'Unknown'}",
  "key": "G",  // Musical key
  "sections": [
    {{
      "label": "Verse",
      "chords": ["G", "G", "C", "G", "D", "D", "G", "G"]
    }},
    {{
      "label": "Chorus",
      "chords": ["C", "C", "G", "G", "D", "D", "G", "G"]
    }}
  ],
  "lyrics": [  // Optional
    {{
      "label": "Verse",
      "lines": ["Line 1", "Line 2", "Line 3", "Line 4"]
    }}
  ]
}}

For bluegrass/folk songs, use standard chord progressions. Each section should have 8 chords (2 measures of 4 beats each). Return ONLY valid JSON, no other text."""

        # Call appropriate LLM provider
        if self.provider == 'openai':
            response_data = self._call_openai(prompt)
        elif self.provider == 'anthropic':
            response_data = self._call_anthropic(prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        # Parse and validate response with Pydantic
        try:
            validated_response = ChartGenerationResponse.model_validate(response_data)
            logger.info(
                f"Successfully generated chord chart for '{song_title}' "
                f"using {self.model} (key={validated_response.key}, "
                f"sections={len(validated_response.sections)})"
            )
            return validated_response
        except ValidationError as e:
            logger.error(f"LLM response validation failed: {e}")
            logger.error(f"Raw response: {response_data}")
            raise

    def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API with JSON mode.

        Args:
            prompt: Prompt for chart generation.

        Returns:
            Parsed JSON response.

        Raises:
            Exception: For API errors.
        """
        try:
            import openai
            import json

            client = openai.OpenAI(api_key=self.openai_api_key)

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a bluegrass/folk music expert. Generate accurate chord charts in JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise Exception("Chart generation service is rate limited. Please try again later.")
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"Chart generation failed: {e}")
        except Exception as e:
            logger.error(f"OpenAI call failed: {e}")
            raise

    def _call_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic API with structured output.

        Args:
            prompt: Prompt for chart generation.

        Returns:
            Parsed JSON response.

        Raises:
            Exception: For API errors.
        """
        try:
            import anthropic
            import json

            client = anthropic.Anthropic(api_key=self.anthropic_api_key)

            message = client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
            )

            content = message.content[0].text

            # Parse JSON from response
            # Claude might wrap JSON in markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

        except anthropic.RateLimitError as e:
            logger.error(f"Anthropic rate limit exceeded: {e}")
            raise Exception("Chart generation service is rate limited. Please try again later.")
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise Exception(f"Chart generation failed: {e}")
        except Exception as e:
            logger.error(f"Anthropic call failed: {e}")
            raise
