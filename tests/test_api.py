import pytest
from httpx import AsyncClient
from main import app
import redis
import os


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def redis_client():
    redis_password = os.getenv("REDIS_PASSWORD")
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=redis_password if redis_password else None,
        decode_responses=True
    )


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code in [200, 503]  # 503 if Redis is down


@pytest.mark.asyncio
async def test_put_get_value(client, redis_client):
    # Clean up first
    redis_client.delete("1234567890abcdef1234567890abcdef")

    # Test PUT
    response = await client.put(
        "/1234567890abcdef1234567890abcdef",
        content="fedcba0987654321fedcba0987654321"
    )
    assert response.status_code == 201

    # Test GET
    response = await client.get("/1234567890abcdef1234567890abcdef")
    assert response.status_code == 200
    assert response.text == "fedcba0987654321fedcba0987654321"


@pytest.mark.asyncio
async def test_invalid_hex_format(client):
    response = await client.put("/invalid", content="alsoinvalid")
    assert response.status_code == 400