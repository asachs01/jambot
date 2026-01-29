"""Tests for the PremiumClient class."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import aiohttp
import asyncio

from src.premium_client import (
    PremiumClient,
    InvalidTokenError,
    InsufficientCreditsError,
    APIConnectionError,
    APIServerError,
    PremiumAPIError,
    CreditBalance,
    GeneratedChart,
    validate_premium_token,
)


class TestPremiumClientInitialization:
    """Test PremiumClient initialization and configuration."""

    def test_init_default_config(self):
        """Should initialize with default config values."""
        with patch('src.premium_client.Config') as mock_config:
            mock_config.PREMIUM_API_BASE_URL = 'https://api.premium.jambot.app'
            mock_config.PREMIUM_API_TIMEOUT = 30

            client = PremiumClient()

            assert client.base_url == 'https://api.premium.jambot.app'
            assert client.timeout == 30
            assert client._session is None

    def test_init_custom_config(self):
        """Should initialize with custom config values."""
        client = PremiumClient(
            base_url='https://custom.api.example.com',
            timeout=60
        )

        assert client.base_url == 'https://custom.api.example.com'
        assert client.timeout == 60

    def test_init_strips_trailing_slash(self):
        """Should strip trailing slash from base URL."""
        client = PremiumClient(base_url='https://api.example.com/')

        assert client.base_url == 'https://api.example.com'

    def test_get_headers(self):
        """Should build correct authorization headers."""
        client = PremiumClient()
        headers = client._get_headers('test_token_123')

        assert headers['Authorization'] == 'Bearer test_token_123'
        assert headers['Content-Type'] == 'application/json'
        assert headers['Accept'] == 'application/json'


class TestPremiumClientSessionManagement:
    """Test session lifecycle management."""

    @pytest.mark.asyncio
    async def test_get_session_creates_new(self):
        """Should create new session if none exists."""
        client = PremiumClient(timeout=30)

        session = await client._get_session()

        assert session is not None
        assert isinstance(session, aiohttp.ClientSession)
        assert not session.closed

        await client.close()

    @pytest.mark.asyncio
    async def test_get_session_reuses_existing(self):
        """Should reuse existing open session."""
        client = PremiumClient()

        session1 = await client._get_session()
        session2 = await client._get_session()

        assert session1 is session2

        await client.close()

    @pytest.mark.asyncio
    async def test_get_session_recreates_closed(self):
        """Should create new session if existing is closed."""
        client = PremiumClient()

        session1 = await client._get_session()
        await client.close()
        session2 = await client._get_session()

        assert session1 is not session2
        assert session1.closed
        assert not session2.closed

        await client.close()

    @pytest.mark.asyncio
    async def test_close_cleans_up_session(self):
        """Should close session and set to None."""
        client = PremiumClient()

        session = await client._get_session()
        assert not session.closed

        await client.close()

        assert session.closed
        assert client._session is None

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self):
        """Should properly cleanup when used as context manager."""
        async with PremiumClient() as client:
            session = await client._get_session()
            assert not session.closed

        assert session.closed


class TestPremiumClientValidateToken:
    """Test token validation endpoint."""

    @pytest.mark.asyncio
    async def test_validate_token_success(self):
        """Should validate token and return tenant info."""
        client = PremiumClient()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'valid': True,
            'tenant_name': 'Test Guild'
        })

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_get_session.return_value = mock_session

            result = await client.validate_token('test_token')

            assert result['valid'] is True
            assert result['tenant_name'] == 'Test Guild'

        await client.close()

    @pytest.mark.asyncio
    async def test_validate_token_invalid(self):
        """Should raise InvalidTokenError for 401 response."""
        client = PremiumClient()

        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.json = AsyncMock(return_value={
            'error': 'Invalid token'
        })

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_get_session.return_value = mock_session

            with pytest.raises(InvalidTokenError) as exc:
                await client.validate_token('bad_token')

            assert 'Invalid token' in str(exc.value)

        await client.close()

    @pytest.mark.asyncio
    async def test_validate_token_connection_error(self):
        """Should raise APIConnectionError on connection failure."""
        client = PremiumClient()

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(side_effect=aiohttp.ClientConnectorError(MagicMock(), OSError()))
            mock_get_session.return_value = mock_session

            with pytest.raises(APIConnectionError) as exc:
                await client.validate_token('test_token')

            assert 'Unable to connect' in str(exc.value)

        await client.close()


class TestPremiumClientGetCredits:
    """Test credit balance retrieval."""

    @pytest.mark.asyncio
    async def test_get_credits_success(self):
        """Should retrieve credit balance for guild."""
        client = PremiumClient()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'credits_remaining': 100,
            'trial_credits_remaining': 5,
            'lifetime_purchased': 200
        })

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_get_session.return_value = mock_session

            result = await client.get_credits('test_token', 123456789)

            assert isinstance(result, CreditBalance)
            assert result.credits_remaining == 100
            assert result.trial_credits_remaining == 5
            assert result.lifetime_purchased == 200

        await client.close()

    @pytest.mark.asyncio
    async def test_get_credits_defaults_missing_fields(self):
        """Should default to 0 for missing credit fields."""
        client = PremiumClient()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={})

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_get_session.return_value = mock_session

            result = await client.get_credits('test_token', 123456789)

            assert result.credits_remaining == 0
            assert result.trial_credits_remaining == 0
            assert result.lifetime_purchased == 0

        await client.close()

    @pytest.mark.asyncio
    async def test_get_credits_invalid_token(self):
        """Should raise InvalidTokenError for invalid token."""
        client = PremiumClient()

        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.json = AsyncMock(return_value={'error': 'Invalid token'})

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_get_session.return_value = mock_session

            with pytest.raises(InvalidTokenError):
                await client.get_credits('bad_token', 123456789)

        await client.close()


class TestPremiumClientGenerateChart:
    """Test chart generation endpoint."""

    @pytest.mark.asyncio
    async def test_generate_chart_success(self):
        """Should generate chart and return result."""
        client = PremiumClient()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'success': True,
            'chart': {
                'title': 'Amazing Grace',
                'artist': 'Traditional',
                'key': 'G',
                'chords': ['G', 'C', 'D']
            },
            'credits_remaining': 99,
            'generation_id': 'gen_abc123'
        })

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_get_session.return_value = mock_session

            result = await client.generate_chart(
                'test_token',
                123456789,
                'Amazing Grace',
                artist='Traditional',
                key='G'
            )

            assert isinstance(result, GeneratedChart)
            assert result.success is True
            assert result.chart['title'] == 'Amazing Grace'
            assert result.credits_remaining == 99
            assert result.generation_id == 'gen_abc123'
            assert result.error is None

        await client.close()

    @pytest.mark.asyncio
    async def test_generate_chart_insufficient_credits(self):
        """Should return failed result for insufficient credits."""
        client = PremiumClient()

        mock_response = MagicMock()
        mock_response.status = 402
        mock_response.json = AsyncMock(return_value={
            'error': 'Insufficient credits',
            'credits_remaining': 0,
            'purchase_url': 'https://premium.jambot.io/purchase'
        })

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_get_session.return_value = mock_session

            result = await client.generate_chart('test_token', 123456789, 'Test Song')

            assert isinstance(result, GeneratedChart)
            assert result.success is False
            assert result.chart is None
            assert result.credits_remaining == 0
            assert result.error == 'insufficient_credits'

        await client.close()

    @pytest.mark.asyncio
    async def test_generate_chart_minimal_params(self):
        """Should generate chart with only required params."""
        client = PremiumClient()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'success': True,
            'chart': {'title': 'Test Song'},
            'credits_remaining': 50,
            'generation_id': 'gen_xyz'
        })

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_get_session.return_value = mock_session

            result = await client.generate_chart('test_token', 123456789, 'Test Song')

            assert result.success is True
            assert result.chart['title'] == 'Test Song'

        await client.close()


class TestPremiumClientCheckoutUrl:
    """Test checkout URL generation."""

    @pytest.mark.asyncio
    async def test_get_checkout_url_success(self):
        """Should retrieve Stripe checkout URL."""
        client = PremiumClient()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'checkout_url': 'https://checkout.stripe.com/session_abc123'
        })

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_get_session.return_value = mock_session

            url = await client.get_checkout_url(
                'test_token',
                'credit_pack_10',
                123456789
            )

            assert url == 'https://checkout.stripe.com/session_abc123'

        await client.close()

    @pytest.mark.asyncio
    async def test_get_checkout_url_with_redirects(self):
        """Should include success/cancel URLs in request."""
        client = PremiumClient()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'checkout_url': 'https://checkout.stripe.com/session_abc123'
        })

        with patch.object(client, '_request') as mock_request:
            mock_request.return_value = {
                'checkout_url': 'https://checkout.stripe.com/session_abc123'
            }

            url = await client.get_checkout_url(
                'test_token',
                'credit_pack_30',
                123456789,
                success_url='https://example.com/success',
                cancel_url='https://example.com/cancel'
            )

            # Verify _request was called with correct data
            call_args = mock_request.call_args
            request_data = call_args[1]['data']

            assert request_data['product_id'] == 'credit_pack_30'
            assert request_data['guild_id'] == 123456789
            assert request_data['success_url'] == 'https://example.com/success'
            assert request_data['cancel_url'] == 'https://example.com/cancel'
            assert url == 'https://checkout.stripe.com/session_abc123'

        await client.close()


class TestPremiumClientErrorHandling:
    """Test error handling across different scenarios."""

    @pytest.mark.asyncio
    async def test_server_error_500(self):
        """Should raise APIServerError for 5xx responses."""
        client = PremiumClient()

        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.json = AsyncMock(return_value={
            'error': 'Internal server error'
        })

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_get_session.return_value = mock_session

            with pytest.raises(APIServerError) as exc:
                await client.validate_token('test_token')

            assert '500' in str(exc.value)
            assert 'Internal server error' in str(exc.value)

        await client.close()

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Should raise APIConnectionError on timeout."""
        client = PremiumClient(timeout=1)

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(side_effect=asyncio.TimeoutError())
            mock_get_session.return_value = mock_session

            with pytest.raises(APIConnectionError) as exc:
                await client.validate_token('test_token')

            assert 'timed out' in str(exc.value)

        await client.close()

    @pytest.mark.asyncio
    async def test_non_json_response_body(self):
        """Should handle non-JSON response bodies."""
        client = PremiumClient()

        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.json = AsyncMock(side_effect=ValueError('Not JSON'))
        mock_response.text = AsyncMock(return_value='Plain text error')

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_get_session.return_value = mock_session

            with pytest.raises(APIServerError) as exc:
                await client.validate_token('test_token')

            assert 'Plain text error' in str(exc.value)

        await client.close()

    @pytest.mark.asyncio
    async def test_generic_400_error(self):
        """Should raise PremiumAPIError for generic 4xx errors."""
        client = PremiumClient()

        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={
            'error': 'Bad request'
        })

        with patch.object(client, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.request = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))
            mock_get_session.return_value = mock_session

            with pytest.raises(PremiumAPIError) as exc:
                await client.validate_token('test_token')

            assert '400' in str(exc.value)
            assert 'Bad request' in str(exc.value)

        await client.close()


class TestConvenienceFunctions:
    """Test standalone convenience functions."""

    @pytest.mark.asyncio
    async def test_validate_premium_token_success(self):
        """Should return True for valid token."""
        with patch('src.premium_client.PremiumClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.validate_token = AsyncMock(return_value={'valid': True})
            mock_client.close = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await validate_premium_token('test_token')

            assert result is True

    @pytest.mark.asyncio
    async def test_validate_premium_token_invalid(self):
        """Should return False for invalid token."""
        with patch('src.premium_client.PremiumClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.validate_token = AsyncMock(return_value={'valid': False})
            mock_client.close = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await validate_premium_token('bad_token')

            assert result is False

    @pytest.mark.asyncio
    async def test_validate_premium_token_connection_error(self):
        """Should return False on connection error."""
        async def mock_aexit(self, exc_type, exc_val, exc_tb):
            return None

        with patch('src.premium_client.PremiumClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.validate_token = AsyncMock(side_effect=APIConnectionError('Connection failed'))
            mock_client.close = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = mock_aexit
            mock_client_class.return_value = mock_client

            result = await validate_premium_token('test_token')

            assert result is False

    @pytest.mark.asyncio
    async def test_validate_premium_token_invalid_error(self):
        """Should return False on InvalidTokenError."""
        async def mock_aexit(self, exc_type, exc_val, exc_tb):
            return None

        with patch('src.premium_client.PremiumClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.validate_token = AsyncMock(side_effect=InvalidTokenError('Bad token'))
            mock_client.close = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = mock_aexit
            mock_client_class.return_value = mock_client

            result = await validate_premium_token('bad_token')

            assert result is False
