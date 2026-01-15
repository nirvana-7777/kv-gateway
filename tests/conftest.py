import os
import sys
import pytest
import fakeredis
from unittest.mock import patch

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)


@pytest.fixture
def mock_redis():
    """Fixture to mock Redis for unit tests."""
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)

    with patch('app.main.redis.Redis') as mock_redis_class:
        mock_redis_class.return_value = fake_redis
        yield fake_redis


@pytest.fixture
def async_client():
    """Fixture for HTTP client."""
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        yield client