"""HTTP client for JamBot Premium API service."""
import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from src.config import Config
from src.logger import logger


class PremiumAPIError(Exception):
    """Base exception for Premium API errors."""
    pass


class InvalidTokenError(PremiumAPIError):
    """Raised when the API token is invalid or expired."""
    pass


class InsufficientCreditsError(PremiumAPIError):
    """Raised when there are not enough credits for an operation."""

    def __init__(self, message: str, credits_remaining: int = 0, purchase_url: Optional[str] = None):
        super().__init__(message)
        self.credits_remaining = credits_remaining
        self.purchase_url = purchase_url


class APIConnectionError(PremiumAPIError):
    """Raised when unable to connect to the Premium API."""
    pass


class APIServerError(PremiumAPIError):
    """Raised when the Premium API returns a server error."""
    pass


@dataclass
class CreditBalance:
    """Credit balance information."""
    credits_remaining: int
    trial_credits_remaining: int
    lifetime_purchased: int


@dataclass
class GeneratedChart:
    """Result of a chart generation request."""
    success: bool
    chart: Optional[Dict[str, Any]]
    credits_remaining: int
    generation_id: Optional[str]
    error: Optional[str] = None
    data_source: Optional[str] = None  # "cache", "ultimate_guitar", "ai_generated"


@dataclass
class TransposedChart:
    """Result of a chart transposition request."""
    success: bool
    chart: Optional[Dict[str, Any]]
    original_key: str
    target_key: str
    semitones: int
    error: Optional[str] = None


class PremiumClient:
    """Async HTTP client for the JamBot Premium API.

    This client communicates with the closed-source premium API service
    for AI chord chart generation and credit management.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """Initialize the premium client.

        Args:
            base_url: Premium API base URL. Uses Config.PREMIUM_API_BASE_URL if not provided.
            timeout: Request timeout in seconds. Uses Config.PREMIUM_API_TIMEOUT if not provided.
        """
        self.base_url = (base_url or Config.PREMIUM_API_BASE_URL).rstrip('/')
        self.timeout = timeout or Config.PREMIUM_API_TIMEOUT
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session.

        Returns:
            Active aiohttp ClientSession.
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _get_headers(self, token: str) -> Dict[str, str]:
        """Build request headers with authentication.

        Args:
            token: Premium API token.

        Returns:
            Headers dictionary.
        """
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        token: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an API request with error handling.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path.
            token: Premium API token.
            data: Request body data (for POST).
            params: Query parameters (for GET).

        Returns:
            Parsed JSON response.

        Raises:
            InvalidTokenError: If token is invalid (401).
            InsufficientCreditsError: If not enough credits (402).
            APIServerError: If server error occurs (5xx).
            APIConnectionError: If connection fails.
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(token)

        try:
            session = await self._get_session()
            async with session.request(
                method,
                url,
                headers=headers,
                json=data,
                params=params
            ) as response:
                # Parse response body
                try:
                    body = await response.json()
                except Exception:
                    body = {"error": await response.text()}

                # Handle errors based on status code
                if response.status == 401:
                    raise InvalidTokenError(
                        body.get("error", "Invalid or expired API token")
                    )

                if response.status == 402:
                    raise InsufficientCreditsError(
                        body.get("error", "Insufficient credits"),
                        credits_remaining=body.get("credits_remaining", 0),
                        purchase_url=body.get("purchase_url")
                    )

                if response.status >= 500:
                    raise APIServerError(
                        f"Premium API server error: {response.status} - {body.get('error', 'Unknown error')}"
                    )

                if response.status >= 400:
                    raise PremiumAPIError(
                        f"Premium API error: {response.status} - {body.get('error', 'Unknown error')}"
                    )

                return body

        except aiohttp.ClientConnectorError as e:
            logger.error(f"Failed to connect to Premium API: {e}")
            raise APIConnectionError(f"Unable to connect to Premium API: {e}")
        except asyncio.TimeoutError:
            logger.error(f"Premium API request timed out after {self.timeout}s")
            raise APIConnectionError(f"Premium API request timed out after {self.timeout}s")

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a premium API token.

        Args:
            token: Premium API token to validate.

        Returns:
            Dict with 'valid' (bool) and 'tenant_name' (str) if valid.

        Raises:
            InvalidTokenError: If token is invalid.
            APIConnectionError: If connection fails.
        """
        logger.debug("Validating premium API token")
        return await self._request("POST", "/api/v1/validate", token)

    async def get_credits(self, token: str, guild_id: int) -> CreditBalance:
        """Get credit balance for a guild.

        Args:
            token: Premium API token.
            guild_id: Discord guild ID.

        Returns:
            CreditBalance dataclass with balance info.

        Raises:
            InvalidTokenError: If token is invalid.
            APIConnectionError: If connection fails.
        """
        logger.debug(f"Getting credit balance for guild {guild_id}")
        response = await self._request(
            "GET",
            "/api/v1/credits",
            token,
            params={"guild_id": str(guild_id)}
        )

        return CreditBalance(
            credits_remaining=response.get("credits_remaining", 0),
            trial_credits_remaining=response.get("trial_credits_remaining", 0),
            lifetime_purchased=response.get("lifetime_purchased", 0)
        )

    async def generate_chart(
        self,
        token: str,
        guild_id: int,
        title: str,
        artist: Optional[str] = None,
        key: Optional[str] = None
    ) -> GeneratedChart:
        """Generate a chord chart using the premium AI service.

        Args:
            token: Premium API token.
            guild_id: Discord guild ID.
            title: Song title to generate chart for.
            artist: Optional artist name for better results.
            key: Optional key to generate the chart in.

        Returns:
            GeneratedChart dataclass with chart data and remaining credits.

        Raises:
            InvalidTokenError: If token is invalid.
            InsufficientCreditsError: If not enough credits.
            APIConnectionError: If connection fails.
        """
        logger.info(f"Generating chart for '{title}' in guild {guild_id}")

        data = {
            "title": title,
            "guild_id": guild_id
        }
        if artist:
            data["artist"] = artist
        if key:
            data["key"] = key

        try:
            response = await self._request("POST", "/api/v1/generate", token, data=data)

            return GeneratedChart(
                success=response.get("success", False),
                chart=response.get("chart"),
                credits_remaining=response.get("credits_remaining", 0),
                generation_id=response.get("generation_id"),
                data_source=response.get("data_source")
            )
        except InsufficientCreditsError as e:
            # Return a failed result instead of raising for easier handling
            return GeneratedChart(
                success=False,
                chart=None,
                credits_remaining=e.credits_remaining,
                generation_id=None,
                error="insufficient_credits"
            )

    async def generate_chart_pdf(
        self,
        token: str,
        guild_id: int,
        title: str,
        artist: Optional[str] = None,
        key: Optional[str] = None
    ) -> bytes:
        """Generate a chord chart PDF directly from the premium API.

        This uses the API's PDF rendering (TNBGJ songbook format) rather than
        local PDF generation. Returns the raw PDF bytes.

        Args:
            token: Premium API token.
            guild_id: Discord guild ID.
            title: Song title to generate chart for.
            artist: Optional artist name for better results.
            key: Optional key to generate the chart in.

        Returns:
            PDF file bytes.

        Raises:
            InvalidTokenError: If token is invalid.
            InsufficientCreditsError: If not enough credits.
            APIConnectionError: If connection fails.
        """
        logger.info(f"Generating chart PDF for '{title}' in guild {guild_id}")

        url = f"{self.base_url}/api/v1/generate?format=pdf"
        headers = self._get_headers(token)

        data = {
            "title": title,
            "guild_id": guild_id
        }
        if artist:
            data["artist"] = artist
        if key:
            data["key"] = key

        try:
            session = await self._get_session()
            async with session.post(url, headers=headers, json=data) as response:
                # Handle errors
                if response.status == 401:
                    raise InvalidTokenError("Invalid or expired API token")
                if response.status == 402:
                    body = await response.json()
                    raise InsufficientCreditsError(
                        "Insufficient credits",
                        credits_remaining=body.get("credits_remaining", 0),
                        purchase_url=body.get("purchase_url")
                    )
                if response.status >= 500:
                    raise APIServerError(f"Premium API server error: {response.status}")
                if response.status >= 400:
                    body = await response.json()
                    raise PremiumAPIError(f"Premium API error: {response.status} - {body.get('error', 'Unknown')}")

                # Return PDF bytes
                return await response.read()

        except aiohttp.ClientConnectorError as e:
            logger.error(f"Failed to connect to Premium API: {e}")
            raise APIConnectionError(f"Unable to connect to Premium API: {e}")
        except asyncio.TimeoutError:
            logger.error(f"Premium API request timed out after {self.timeout}s")
            raise APIConnectionError(f"Premium API request timed out after {self.timeout}s")

    async def render_pdf(
        self,
        token: str,
        chart_data: Dict[str, Any]
    ) -> bytes:
        """Render chart data to PDF using the API's TNBGJ format.

        This does NOT charge credits - it only renders existing chart data
        that was previously generated.

        Args:
            token: Premium API token.
            chart_data: Chart data dict with title, key, sections, and optional lyrics.

        Returns:
            PDF file bytes.

        Raises:
            InvalidTokenError: If token is invalid.
            APIConnectionError: If connection fails.
        """
        logger.info(f"Rendering PDF for '{chart_data.get('title', 'Unknown')}'")

        url = f"{self.base_url}/api/v1/render-pdf"
        headers = self._get_headers(token)

        try:
            session = await self._get_session()
            async with session.post(url, headers=headers, json=chart_data) as response:
                if response.status == 401:
                    raise InvalidTokenError("Invalid or expired API token")
                if response.status >= 500:
                    raise APIServerError(f"Premium API server error: {response.status}")
                if response.status >= 400:
                    body = await response.json()
                    raise PremiumAPIError(f"Premium API error: {response.status} - {body.get('error', 'Unknown')}")

                return await response.read()

        except aiohttp.ClientConnectorError as e:
            logger.error(f"Failed to connect to Premium API: {e}")
            raise APIConnectionError(f"Unable to connect to Premium API: {e}")
        except asyncio.TimeoutError:
            logger.error(f"Premium API request timed out after {self.timeout}s")
            raise APIConnectionError(f"Premium API request timed out after {self.timeout}s")

    async def get_checkout_url(
        self,
        token: str,
        product_id: str,
        guild_id: int,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> str:
        """Get a Stripe checkout URL for purchasing credits.

        Args:
            token: Premium API token.
            product_id: Product ID (e.g., 'credit_pack_10', 'credit_pack_25', 'credit_pack_50').
            guild_id: Discord guild ID.
            success_url: URL to redirect to on successful purchase.
            cancel_url: URL to redirect to on cancelled purchase.

        Returns:
            Stripe checkout URL.

        Raises:
            InvalidTokenError: If token is invalid.
            APIConnectionError: If connection fails.
        """
        logger.debug(f"Getting checkout URL for {product_id} in guild {guild_id}")

        data = {
            "product_id": product_id,
            "guild_id": guild_id
        }
        if success_url:
            data["success_url"] = success_url
        if cancel_url:
            data["cancel_url"] = cancel_url

        response = await self._request("POST", "/api/v1/checkout", token, data=data)
        return response.get("checkout_url", "")

    async def render_pdf(self, token: str, chart_data: Dict[str, Any]) -> bytes:
        """Render a chord chart to PDF via the premium API.

        This endpoint does NOT consume credits - it only renders existing chart data.

        Args:
            token: Premium API token.
            chart_data: Chart data dict with title, key, sections, and optional lyrics.
                Must conform to the ChartData schema:
                - title: str
                - key: str
                - sections: List[{label: str, chords: List[str], rows: int}]
                - lyrics: Optional[List[{label: str, lines: List[str]}]]

        Returns:
            PDF file bytes.

        Raises:
            InvalidTokenError: If token is invalid.
            APIConnectionError: If connection fails.
            PremiumAPIError: If chart data is invalid.
        """
        logger.debug(f"Rendering PDF for chart: {chart_data.get('title', 'Unknown')}")

        url = f"{self.base_url}/api/v1/render-pdf"
        headers = self._get_headers(token)

        try:
            session = await self._get_session()
            async with session.post(url, headers=headers, json=chart_data) as response:
                if response.status == 401:
                    raise InvalidTokenError("Invalid or expired API token")

                if response.status >= 400:
                    try:
                        body = await response.json()
                        error_msg = body.get("error", "Unknown error")
                    except Exception:
                        error_msg = await response.text()
                    raise PremiumAPIError(f"PDF render failed: {response.status} - {error_msg}")

                return await response.read()

        except aiohttp.ClientConnectorError as e:
            logger.error(f"Failed to connect to Premium API: {e}")
            raise APIConnectionError(f"Unable to connect to Premium API: {e}")
        except asyncio.TimeoutError:
            logger.error(f"Premium API request timed out after {self.timeout}s")
            raise APIConnectionError(f"Premium API request timed out after {self.timeout}s")

    async def transpose_chart(
        self,
        token: str,
        chart_data: Dict[str, Any],
        target_key: str
    ) -> TransposedChart:
        """Transpose a chord chart to a different key via the premium API.

        This endpoint does NOT consume credits - it only transforms existing data.

        Args:
            token: Premium API token.
            chart_data: Chart data dict conforming to ChartData schema.
            target_key: Target key to transpose to (e.g., 'G', 'Am', 'Bb').

        Returns:
            TransposedChart with the transposed chart data.

        Raises:
            InvalidTokenError: If token is invalid.
            APIConnectionError: If connection fails.
            PremiumAPIError: If transposition fails (e.g., invalid key).
        """
        logger.debug(f"Transposing chart '{chart_data.get('title')}' to key {target_key}")

        data = {
            "chart": chart_data,
            "target_key": target_key
        }

        try:
            response = await self._request("POST", "/api/v1/transpose", token, data=data)

            return TransposedChart(
                success=response.get("success", False),
                chart=response.get("chart"),
                original_key=response.get("original_key", ""),
                target_key=response.get("target_key", target_key),
                semitones=response.get("semitones", 0),
                error=response.get("error")
            )
        except PremiumAPIError as e:
            return TransposedChart(
                success=False,
                chart=None,
                original_key=chart_data.get("key", ""),
                target_key=target_key,
                semitones=0,
                error=str(e)
            )

    async def create_manual_chart(
        self,
        token: str,
        guild_id: int,
        title: str,
        key: str,
        sections: List[Dict[str, Any]],
        lyrics: Optional[List[Dict[str, Any]]] = None,
        render_pdf: bool = False
    ) -> Dict[str, Any]:
        """Create a chart from manual user input and optionally render to PDF.

        This method does NOT consume credits - it's for user-created charts, not AI generation.
        The chart data is validated and formatted, then optionally rendered to PDF.

        Args:
            token: Premium API token.
            guild_id: Discord guild ID.
            title: Song title.
            key: Key string (e.g., 'G', 'Am').
            sections: List of section dicts with 'label', 'chords', and optional 'rows'.
            lyrics: Optional list of lyric dicts with 'label' and 'lines'.
            render_pdf: If True, also render and return PDF bytes.

        Returns:
            Dict with:
                - chart: The formatted chart data
                - pdf_bytes: PDF bytes if render_pdf=True, else None

        Raises:
            InvalidTokenError: If token is invalid.
            APIConnectionError: If connection fails.
        """
        logger.info(f"Creating manual chart: title='{title}', key='{key}', guild={guild_id}")

        # Build chart data in the format expected by the premium API
        chart_data = {
            "title": title,
            "key": key,
            "sections": sections,
        }
        if lyrics:
            chart_data["lyrics"] = lyrics

        result = {
            "chart": chart_data,
            "pdf_bytes": None
        }

        if render_pdf:
            result["pdf_bytes"] = await self.render_pdf(token, chart_data)

        return result

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Convenience function for one-off requests
async def validate_premium_token(token: str) -> bool:
    """Quick validation of a premium token.

    Args:
        token: Premium API token to validate.

    Returns:
        True if valid, False otherwise.
    """
    try:
        async with PremiumClient() as client:
            result = await client.validate_token(token)
            return result.get("valid", False)
    except (InvalidTokenError, APIConnectionError):
        return False
