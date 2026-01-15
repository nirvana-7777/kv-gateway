import asyncio
import os
import sys
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

# Add the parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint_success(client):
    """Test health endpoint when Redis is available"""
    print("\n=== DEBUG test_health_endpoint_success ===")

    # Mock redis_client.ping to succeed
    with patch("app.main.redis_client.ping") as mock_ping:
        mock_ping.return_value = True

        response = await client.get("/health")
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_endpoint_redis_down(client):
    """Test health endpoint when Redis is down"""
    print("\n=== DEBUG test_health_endpoint_redis_down ===")
    import redis

    # Mock redis_client.ping to raise an exception
    with patch("app.main.redis_client.ping") as mock_ping:
        mock_ping.side_effect = redis.exceptions.RedisError("Connection failed")

        response = await client.get("/health")
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")

        assert response.status_code == 503
        assert "Redis unavailable" in response.json()["detail"]


@pytest.mark.asyncio
async def test_put_get_value(client, mock_redis):
    print("\n=== DEBUG test_put_get_value ===")
    # Clean up first
    mock_redis.delete("1234567890abcdef1234567890abcdef")

    # Mock the redis operations in your app
    with patch("app.main.redis_client", mock_redis):
        # Test PUT
        response = await client.put(
            "/1234567890abcdef1234567890abcdef",
            content="fedcba0987654321fedcba0987654321",
        )
        print(f"PUT Response status: {response.status_code}")
        assert response.status_code == 201

        # Test GET
        response = await client.get("/1234567890abcdef1234567890abcdef")
        print(f"GET Response status: {response.status_code}")
        print(f"GET Response text: {response.text}")
        assert response.status_code == 200

        # The response is JSON-encoded (has quotes), so strip them
        response_text = response.text
        if response_text.startswith('"') and response_text.endswith('"'):
            response_text = response_text[1:-1]

        assert response_text == "fedcba0987654321fedcba0987654321"


@pytest.mark.asyncio
async def test_invalid_hex_format(client):
    response = await client.put("/invalid", content="alsoinvalid")
    assert response.status_code == 400
