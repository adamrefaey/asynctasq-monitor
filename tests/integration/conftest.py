"""Integration test configuration and fixtures.

This module provides fixtures for integration testing with real services.
Following pytest-asyncio best practices (2024):
- Use @pytest_asyncio.fixture for async fixtures
- Use 'strict' asyncio_mode with explicit @pytest.mark.asyncio
- Use httpx.AsyncClient with ASGITransport for FastAPI async tests
- Use separate test database/channels to avoid conflicts

References:
- FastAPI async tests: https://fastapi.tiangolo.com/advanced/async-tests/
- pytest-asyncio decorators: https://pytest-asyncio.readthedocs.io/en/stable/reference/decorators/

Note: This module does NOT define an 'app' fixture because:
1. The sync integration tests rely on the 'app' fixture from tests/conftest.py
   which provides mocked services for deterministic testing.
2. The async tests also use 'async_client' from tests/conftest.py which
   depends on the mocked 'app' fixture.

For true end-to-end integration tests that require real services (Redis, etc.),
define a separate fixture like 'integration_app' and use it explicitly.
"""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from redis.asyncio import Redis


# NOTE: The 'app' and 'async_client' fixtures come from tests/conftest.py
# which provides mocked services for predictable test behavior.
# Do NOT shadow them here unless you need real integration testing.


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[Redis]:
    """Real Redis client for integration tests.

    Uses a separate database (DB 15) to avoid conflicts with development data.
    Flushes the test database before yielding to ensure clean state.

    Example:
        @pytest.mark.asyncio
        async def test_event_emission(redis_client):
            await redis_client.set("test_key", "test_value")
            value = await redis_client.get("test_key")
            assert value == b"test_value"
    """
    from redis.asyncio import Redis

    client = Redis.from_url("redis://localhost:6379/15")  # Use test DB
    try:
        await client.ping()  # type: ignore[misc]
        await client.flushdb()  # type: ignore[misc]
        yield client
    except Exception:
        pytest.skip("Redis not available for integration tests")
    finally:
        try:
            await client.aclose()
        except Exception:
            pass
