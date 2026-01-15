import pytest
import fakeredis
import os
from unittest.mock import patch


@pytest.fixture
def mock_redis():
    """Fixture to mock Redis for unit tests."""
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)

    with patch('main.redis.Redis') as mock_redis_class:
        mock_redis_class.return_value = fake_redis
        yield fake_redis


@pytest.fixture
async def async_client():
    """Fixture for async HTTP client."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        yield client