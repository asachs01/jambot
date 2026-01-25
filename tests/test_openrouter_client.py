"""Tests for OpenRouter API client."""
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import aiohttp
from aiohttp import web
from src.openrouter_client import OpenRouterClient


# --- Initialization Tests ---

class TestOpenRouterClientInitialization:
    """Test client initialization."""

    def test_initializes_with_env_var(self, monkeypatch):
        """Test initialization with environment variable."""
        # Mock Config.OPENROUTER_API_KEY directly
        with patch('src.openrouter_client.Config') as mock_config:
            mock_config.OPENROUTER_API_KEY = 'test-api-key-from-env'
            client = OpenRouterClient()

            assert client.api_key == 'test-api-key-from-env'
            assert client.base_url == 'https://openrouter.ai/api/v1'
            assert client.primary_model == 'deepseek/deepseek-chat:v3'
            assert client.fallback_model == 'meta-llama/llama-3.1-70b-instruct:free'
            assert client.current_model == 'deepseek/deepseek-chat:v3'
            assert client.max_retries == 3

    def test_initializes_with_passed_key(self):
        """Test initialization with explicitly passed API key."""
        client = OpenRouterClient(api_key='test-passed-key')

        assert client.api_key == 'test-passed-key'

    def test_raises_on_missing_key(self, monkeypatch):
        """Test that initialization fails without API key."""
        monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)

        with pytest.raises(ValueError) as exc_info:
            OpenRouterClient()

        assert 'OpenRouter API key not found' in str(exc_info.value)

    def test_sets_correct_defaults(self):
        """Test that default values are set correctly."""
        client = OpenRouterClient(api_key='test-key')

        assert client.base_url == 'https://openrouter.ai/api/v1'
        assert client.max_retries == 3
        assert client.current_model == client.primary_model


# --- Chat Completion Tests ---

class TestChatCompletion:
    """Test chat completion functionality."""

    @pytest.mark.asyncio
    async def test_successful_completion_returns_metadata(
        self,
        sample_openrouter_response
    ):
        """Test successful completion returns content and metadata."""
        client = OpenRouterClient(api_key='test-key')

        with patch.object(
            client,
            '_make_request',
            new_callable=AsyncMock,
            return_value=sample_openrouter_response
        ):
            result = await client.chat_completion([
                {"role": "user", "content": "Hello"}
            ])

            assert 'content' in result
            assert 'metadata' in result
            assert result['metadata']['prompt_tokens'] == 10
            assert result['metadata']['completion_tokens'] == 20
            assert 'latency_ms' in result['metadata']
            assert 'cost_usd' in result['metadata']
            assert result['metadata']['model_used'] == 'deepseek/deepseek-chat:v3'

        await client.close()

    @pytest.mark.asyncio
    async def test_tracks_prompt_tokens_accurately(
        self,
        sample_openrouter_response
    ):
        """Test prompt token tracking."""
        client = OpenRouterClient(api_key='test-key')

        with patch.object(
            client,
            '_make_request',
            new_callable=AsyncMock,
            return_value=sample_openrouter_response
        ):
            result = await client.chat_completion([
                {"role": "user", "content": "Test message"}
            ])

            assert result['metadata']['prompt_tokens'] == 10

        await client.close()

    @pytest.mark.asyncio
    async def test_tracks_completion_tokens_accurately(
        self,
        sample_openrouter_response
    ):
        """Test completion token tracking."""
        client = OpenRouterClient(api_key='test-key')

        with patch.object(
            client,
            '_make_request',
            new_callable=AsyncMock,
            return_value=sample_openrouter_response
        ):
            result = await client.chat_completion([
                {"role": "user", "content": "Test"}
            ])

            assert result['metadata']['completion_tokens'] == 20

        await client.close()

    @pytest.mark.asyncio
    async def test_calculates_latency_ms(self):
        """Test latency measurement."""
        client = OpenRouterClient(api_key='test-key')

        async def mock_request(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms delay
            return {
                "content": "Response",
                "metadata": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "latency_ms": 50.0,
                    "cost_usd": 0.0,
                    "model_used": "test-model"
                }
            }

        with patch.object(
            client,
            '_make_request',
            new_callable=AsyncMock,
            side_effect=mock_request
        ):
            result = await client.chat_completion([
                {"role": "user", "content": "Test"}
            ])

            # Latency should be around 50ms (allow some variance)
            assert 40 <= result['metadata']['latency_ms'] <= 100

        await client.close()

    @pytest.mark.asyncio
    async def test_calculates_cost_usd_deepseek(self):
        """Test cost calculation for deepseek model."""
        client = OpenRouterClient(api_key='test-key')

        # 10 prompt tokens, 20 completion tokens
        # Cost = (10/1M * 0.14) + (20/1M * 0.28)
        # Cost = 0.0000014 + 0.0000056 = 0.000007
        expected_cost = (10 / 1_000_000 * 0.14) + (20 / 1_000_000 * 0.28)

        cost = client._calculate_cost(
            10,
            20,
            'deepseek/deepseek-chat:v3'
        )

        assert abs(cost - expected_cost) < 0.000001

        await client.close()

    @pytest.mark.asyncio
    async def test_calculates_cost_usd_fallback_free(self):
        """Test cost calculation for free fallback model."""
        client = OpenRouterClient(api_key='test-key')

        cost = client._calculate_cost(
            10,
            20,
            'meta-llama/llama-3.1-70b-instruct:free'
        )

        assert cost == 0.0

        await client.close()


# --- Retry Logic Tests ---

class TestRetryLogic:
    """Test retry and backoff logic."""

    @pytest.mark.asyncio
    async def test_retries_on_rate_limit_429(self):
        """Test retry on 429 rate limit."""
        client = OpenRouterClient(api_key='test-key')

        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # First call returns 429
                error = aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=429,
                    message='Rate limited',
                    headers={'Retry-After': '1'}
                )
                raise error
            # Second call succeeds
            return {
                "content": "Success",
                "metadata": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "latency_ms": 50.0,
                    "cost_usd": 0.0,
                    "model_used": "test-model"
                }
            }

        with patch.object(
            client,
            '_make_request',
            new_callable=AsyncMock,
            side_effect=mock_request
        ):
            result = await client.chat_completion([
                {"role": "user", "content": "Test"}
            ])

            assert call_count == 2
            assert result['content'] == 'Success'

        await client.close()

    @pytest.mark.asyncio
    async def test_retries_on_server_error_500(self):
        """Test retry on 500 server error."""
        client = OpenRouterClient(api_key='test-key')

        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                error = aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=500,
                    message='Internal Server Error'
                )
                raise error
            return {
                "content": "Success",
                "metadata": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "latency_ms": 50.0,
                    "cost_usd": 0.0,
                    "model_used": "test-model"
                }
            }

        with patch.object(
            client,
            '_make_request',
            new_callable=AsyncMock,
            side_effect=mock_request
        ):
            result = await client.chat_completion([
                {"role": "user", "content": "Test"}
            ])

            assert call_count == 2
            assert result['content'] == 'Success'

        await client.close()

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff delays."""
        client = OpenRouterClient(api_key='test-key')

        call_count = 0
        delays = []

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                error = aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=500,
                    message='Server Error'
                )
                raise error
            return {
                "content": "Success",
                "metadata": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "latency_ms": 50.0,
                    "cost_usd": 0.0,
                    "model_used": "test-model"
                }
            }

        original_sleep = asyncio.sleep

        async def track_sleep(seconds):
            delays.append(seconds)
            await original_sleep(0)  # Don't actually wait in tests

        with patch.object(
            client,
            '_make_request',
            new_callable=AsyncMock,
            side_effect=mock_request
        ):
            with patch('asyncio.sleep', side_effect=track_sleep):
                await client.chat_completion([
                    {"role": "user", "content": "Test"}
                ])

                # Exponential backoff: 2^0=1, 2^1=2
                assert delays == [1, 2]

        await client.close()

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """Test that exception is raised after max retries."""
        client = OpenRouterClient(api_key='test-key')

        async def mock_request(*args, **kwargs):
            error = aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=500,
                message='Persistent Error'
            )
            raise error

        with patch.object(
            client,
            '_make_request',
            new_callable=AsyncMock,
            side_effect=mock_request
        ):
            # Patch sleep to speed up test
            with patch('asyncio.sleep', new_callable=AsyncMock):
                with pytest.raises(Exception) as exc_info:
                    await client.chat_completion([
                        {"role": "user", "content": "Test"}
                    ])

                assert 'Failed after 3 attempts' in str(exc_info.value)

        await client.close()

    @pytest.mark.asyncio
    async def test_respects_retry_after_header(self):
        """Test that Retry-After header is respected."""
        client = OpenRouterClient(api_key='test-key')

        call_count = 0
        sleep_durations = []

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                error = aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=429,
                    message='Rate limited',
                    headers={'Retry-After': '5'}
                )
                raise error
            return {
                "content": "Success",
                "metadata": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "latency_ms": 50.0,
                    "cost_usd": 0.0,
                    "model_used": "test-model"
                }
            }

        async def track_sleep(seconds):
            sleep_durations.append(seconds)

        with patch.object(
            client,
            '_make_request',
            new_callable=AsyncMock,
            side_effect=mock_request
        ):
            with patch('asyncio.sleep', side_effect=track_sleep):
                await client.chat_completion([
                    {"role": "user", "content": "Test"}
                ])

                # Should respect Retry-After: 5
                assert 5 in sleep_durations

        await client.close()


# --- Model Fallback Tests ---

class TestModelFallback:
    """Test model fallback logic."""

    @pytest.mark.asyncio
    async def test_fallback_on_primary_500(self):
        """Test fallback triggers on primary model 500 error."""
        client = OpenRouterClient(api_key='test-key')

        assert client.current_model == 'deepseek/deepseek-chat:v3'

        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # Trigger fallback
                error = aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=500,
                    message='Server Error'
                )
                raise error
            return {
                "content": "Success",
                "metadata": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "latency_ms": 50.0,
                    "cost_usd": 0.0,
                    "model_used": "meta-llama/llama-3.1-70b-instruct:free"
                }
            }

        with patch.object(
            client,
            '_make_request',
            new_callable=AsyncMock,
            side_effect=mock_request
        ):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                await client.chat_completion([
                    {"role": "user", "content": "Test"}
                ])

                # Should have switched to fallback
                assert client.current_model == 'meta-llama/llama-3.1-70b-instruct:free'

        await client.close()

    @pytest.mark.asyncio
    async def test_subsequent_calls_use_fallback(self):
        """Test that subsequent calls use fallback after trigger."""
        client = OpenRouterClient(api_key='test-key')

        # Manually trigger fallback
        client._trigger_fallback()

        assert client.current_model == 'meta-llama/llama-3.1-70b-instruct:free'

        # Next call should use fallback model
        with patch.object(
            client,
            '_make_request',
            new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = {
                "content": "Success",
                "metadata": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "latency_ms": 50.0,
                    "cost_usd": 0.0,
                    "model_used": "meta-llama/llama-3.1-70b-instruct:free"
                }
            }

            await client.chat_completion([
                {"role": "user", "content": "Test"}
            ])

            # Verify fallback model was used
            mock_req.assert_called_once()
            call_args = mock_req.call_args
            assert call_args[0][1] == 'meta-llama/llama-3.1-70b-instruct:free'

        await client.close()

    @pytest.mark.asyncio
    async def test_no_fallback_on_429(self):
        """Test fallback does NOT trigger on 429."""
        client = OpenRouterClient(api_key='test-key')

        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                error = aiohttp.ClientResponseError(
                    request_info=MagicMock(),
                    history=(),
                    status=429,
                    message='Rate limited',
                    headers={'Retry-After': '1'}
                )
                raise error
            return {
                "content": "Success",
                "metadata": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "latency_ms": 50.0,
                    "cost_usd": 0.0,
                    "model_used": "deepseek/deepseek-chat:v3"
                }
            }

        with patch.object(
            client,
            '_make_request',
            new_callable=AsyncMock,
            side_effect=mock_request
        ):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                await client.chat_completion([
                    {"role": "user", "content": "Test"}
                ])

                # Should still be using primary model
                assert client.current_model == 'deepseek/deepseek-chat:v3'

        await client.close()

    @pytest.mark.asyncio
    async def test_fallback_logs_event(self, caplog):
        """Test that fallback is logged."""
        client = OpenRouterClient(api_key='test-key')

        client._trigger_fallback()

        assert 'Triggering fallback' in caplog.text
        assert 'deepseek/deepseek-chat:v3' in caplog.text
        assert 'meta-llama/llama-3.1-70b-instruct:free' in caplog.text

        await client.close()


# --- Async Client Tests ---

class TestAsyncClient:
    """Test async functionality."""

    @pytest.mark.asyncio
    async def test_uses_aiohttp_session(self):
        """Test that aiohttp session is used."""
        client = OpenRouterClient(api_key='test-key')

        # Session should be created on first request
        assert client._session is None

        # Create a proper async context manager mock
        class MockResponse:
            def __init__(self):
                self.status = 200

            async def json(self):
                return {
                    'choices': [{'message': {'content': 'Test'}}],
                    'usage': {'prompt_tokens': 10, 'completion_tokens': 20}
                }

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.post = MagicMock(return_value=MockResponse())
        mock_session.close = AsyncMock()

        with patch.object(aiohttp, 'ClientSession', return_value=mock_session):
            # Trigger request - session will be created in _make_request
            await client._make_request([{"role": "user", "content": "Hi"}], "test-model")

            # Session should be created
            assert client._session is not None

        await client.close()

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager support."""
        async with OpenRouterClient(api_key='test-key') as client:
            assert client.api_key == 'test-key'

        # Session should be closed after exit
        assert client._session is None or client._session.closed

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test multiple concurrent requests."""
        client = OpenRouterClient(api_key='test-key')

        with patch.object(
            client,
            '_make_request',
            new_callable=AsyncMock,
            return_value={
                "content": "Response",
                "metadata": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "latency_ms": 50.0,
                    "cost_usd": 0.0,
                    "model_used": "test-model"
                }
            }
        ):
            results = await asyncio.gather(
                client.chat_completion([{"role": "user", "content": "1"}]),
                client.chat_completion([{"role": "user", "content": "2"}]),
                client.chat_completion([{"role": "user", "content": "3"}]),
            )

            assert len(results) == 3
            for result in results:
                assert result['content'] == 'Response'

        await client.close()

    @pytest.mark.asyncio
    async def test_proper_session_cleanup(self):
        """Test session is properly cleaned up."""
        client = OpenRouterClient(api_key='test-key')

        # Create a mock session
        client._session = AsyncMock()
        client._session.closed = False

        await client.close()

        # Session should be closed
        client._session.close.assert_called_once()


# --- Cost Calculation Tests ---

class TestCostCalculation:
    """Test cost calculation logic."""

    @pytest.mark.asyncio
    async def test_deepseek_pricing_accurate(self):
        """Test deepseek model pricing."""
        client = OpenRouterClient(api_key='test-key')

        # 1000 prompt tokens, 2000 completion tokens
        # Cost = (1000/1M * 0.14) + (2000/1M * 0.28)
        # Cost = 0.00014 + 0.00056 = 0.0007
        expected_cost = (1000 / 1_000_000 * 0.14) + (2000 / 1_000_000 * 0.28)

        cost = client._calculate_cost(
            1000,
            2000,
            'deepseek/deepseek-chat:v3'
        )

        assert abs(cost - expected_cost) < 0.0000001

        await client.close()

    @pytest.mark.asyncio
    async def test_fallback_free_model_zero_cost(self):
        """Test free model has zero cost."""
        client = OpenRouterClient(api_key='test-key')

        cost = client._calculate_cost(
            1000,
            2000,
            'meta-llama/llama-3.1-70b-instruct:free'
        )

        assert cost == 0.0

        await client.close()

    @pytest.mark.asyncio
    async def test_handles_unknown_model(self, caplog):
        """Test unknown model defaults to zero cost with warning."""
        client = OpenRouterClient(api_key='test-key')

        cost = client._calculate_cost(
            1000,
            2000,
            'unknown-model'
        )

        assert cost == 0.0
        assert 'Pricing not found for model unknown-model' in caplog.text

        await client.close()
