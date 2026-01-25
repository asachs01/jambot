"""OpenRouter API integration for Jambot."""
import asyncio
import time
from typing import List, Dict, Any, Optional
import aiohttp
from src.config import Config
from src.logger import logger


class OpenRouterClient:
    """Async OpenRouter API client with model fallback and cost tracking."""

    # OpenRouter API pricing (per 1M tokens)
    PRICING = {
        "deepseek/deepseek-chat:v3": {
            "prompt": 0.14,  # $0.14 per 1M prompt tokens
            "completion": 0.28,  # $0.28 per 1M completion tokens
        },
        "meta-llama/llama-3.1-70b-instruct:free": {
            "prompt": 0.0,  # Free model
            "completion": 0.0,
        },
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key. If None, uses OPENROUTER_API_KEY env var.

        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or Config.OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.base_url = "https://openrouter.ai/api/v1"
        self.primary_model = "deepseek/deepseek-chat:v3"
        self.fallback_model = "meta-llama/llama-3.1-70b-instruct:free"
        self.current_model = self.primary_model
        self.max_retries = 3
        self._session = None

        logger.info(
            f"OpenRouter client initialized with primary model: {self.primary_model}, "
            f"fallback: {self.fallback_model}"
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Perform async chat completion with OpenRouter API.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            **kwargs: Additional parameters to pass to the API (e.g., temperature, max_tokens).

        Returns:
            Dictionary containing:
                - content (str): The response text
                - metadata (dict): Request metadata with:
                    - prompt_tokens (int)
                    - completion_tokens (int)
                    - latency_ms (float)
                    - cost_usd (float)
                    - model_used (str)

        Raises:
            Exception: If API call fails after all retries.
        """
        return await self._retry_api_call(
            self._make_request,
            messages,
            self.current_model,
            **kwargs
        )

    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP POST request to OpenRouter API.

        Args:
            messages: List of message dicts.
            model: Model identifier to use.
            **kwargs: Additional API parameters.

        Returns:
            Dictionary with content and metadata.

        Raises:
            aiohttp.ClientError: On network/HTTP errors.
        """
        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }

        # Create session if needed
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

        try:
            async with self._session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                latency_ms = (time.time() - start_time) * 1000

                response_data = await response.json()

                # Handle error responses
                if response.status >= 400:
                    error_message = response_data.get('error', {}).get('message', 'Unknown error')
                    logger.error(f"OpenRouter API error {response.status}: {error_message}")
                    response.raise_for_status()

                # Extract usage metadata
                usage = response_data.get('usage', {})
                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)

                # Calculate cost
                cost_usd = self._calculate_cost(prompt_tokens, completion_tokens, model)

                # Extract response content
                content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')

                logger.debug(
                    f"OpenRouter request completed: {prompt_tokens} prompt tokens, "
                    f"{completion_tokens} completion tokens, {latency_ms:.2f}ms, ${cost_usd:.6f}"
                )

                return {
                    "content": content,
                    "metadata": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "latency_ms": latency_ms,
                        "cost_usd": cost_usd,
                        "model_used": model,
                    }
                }

        except aiohttp.ClientError as e:
            logger.error(f"Network error calling OpenRouter API: {e}")
            raise

    async def _retry_api_call(self, func, *args, **kwargs) -> Any:
        """Retry API calls with exponential backoff.

        Args:
            func: Async function to call.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            Result from the function.

        Raises:
            Exception: If all retries fail.
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Attempting API call (attempt {attempt + 1}/{self.max_retries})"
                )
                result = await func(*args, **kwargs)
                logger.debug("API call successful")
                return result

            except aiohttp.ClientResponseError as e:
                last_exception = e
                logger.error(f"OpenRouter API error: {e.status} - {e.message}")

                # Handle rate limiting (429)
                if e.status == 429:
                    retry_after = 1
                    if e.headers and 'Retry-After' in e.headers:
                        try:
                            retry_after = int(e.headers['Retry-After'])
                        except ValueError:
                            pass
                    logger.warning(
                        f"Rate limited. Retrying after {retry_after}s "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(retry_after)

                # Handle server errors (5xx)
                elif e.status >= 500:
                    # Trigger fallback on primary model 500 error
                    if e.status == 500 and self.current_model == self.primary_model:
                        self._trigger_fallback()

                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Server error {e.status}. Retrying in {wait_time}s "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(wait_time)

                else:
                    # Non-retryable error
                    logger.error(f"Unrecoverable API error: {e}")
                    raise

            except aiohttp.ClientError as e:
                last_exception = e
                logger.error(f"Network error: {type(e).__name__}: {e}")
                if attempt == self.max_retries - 1:
                    raise

                wait_time = 2 ** attempt
                logger.warning(
                    f"Network error. Retrying in {wait_time}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(wait_time)

            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error: {type(e).__name__}: {e}")
                if attempt == self.max_retries - 1:
                    raise

                wait_time = 2 ** attempt
                logger.warning(
                    f"Unexpected error. Retrying in {wait_time}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(wait_time)

        # All retries exhausted
        raise Exception(
            f"Failed after {self.max_retries} attempts. Last error: {last_exception}"
        )

    def _trigger_fallback(self):
        """Switch from primary model to fallback model."""
        if self.current_model == self.primary_model:
            logger.warning(
                f"Triggering fallback: switching from {self.primary_model} "
                f"to {self.fallback_model}"
            )
            self.current_model = self.fallback_model
        else:
            logger.debug("Already using fallback model")

    def _calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str
    ) -> float:
        """Calculate request cost in USD.

        Args:
            prompt_tokens: Number of prompt tokens used.
            completion_tokens: Number of completion tokens generated.
            model: Model identifier.

        Returns:
            Cost in USD.
        """
        # Get pricing for the model
        pricing = self.PRICING.get(model)

        if not pricing:
            logger.warning(
                f"Pricing not found for model {model}, defaulting to $0.00"
            )
            return 0.0

        # Calculate cost (pricing is per 1M tokens)
        prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]

        return prompt_cost + completion_cost

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("OpenRouter client session closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
