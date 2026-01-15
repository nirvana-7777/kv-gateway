import os
import sys
from unittest.mock import MagicMock, patch

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
    with patch("app.main.redis_client.ping") as mock_ping:
        mock_ping.return_value = True
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_endpoint_redis_down(client):
    """Test health endpoint when Redis is down"""
    import redis

    with patch("app.main.redis_client.ping") as mock_ping:
        mock_ping.side_effect = redis.exceptions.RedisError("Connection failed")
        response = await client.get("/health")
        assert response.status_code == 503
        assert "Redis unavailable" in response.json()["detail"]


@pytest.mark.asyncio
async def test_put_get_value(client, mock_redis):
    with patch("app.main.redis_client", mock_redis):
        # Test PUT
        response = await client.put(
            "/1234567890abcdef1234567890abcdef",
            content="fedcba0987654321fedcba0987654321",
        )
        assert response.status_code == 201

        # Test GET
        response = await client.get("/1234567890abcdef1234567890abcdef")
        assert response.status_code == 200
        response_text = response.text
        if response_text.startswith('"') and response_text.endswith('"'):
            response_text = response_text[1:-1]
        assert response_text == "fedcba0987654321fedcba0987654321"


@pytest.mark.asyncio
async def test_invalid_hex_format(client):
    response = await client.put("/invalid", content="alsoinvalid")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_value_success(client, mock_redis):
    with patch("app.main.redis_client", mock_redis):
        # First create a key
        response = await client.put(
            "/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            content="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        )
        assert response.status_code == 201

        # Verify it exists
        response = await client.get("/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        assert response.status_code == 200

        # Delete it
        response = await client.delete("/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        assert response.status_code == 200

        # Verify it's gone
        response = await client.get("/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_value_not_found(client, mock_redis):
    with patch("app.main.redis_client", mock_redis):
        response = await client.delete("/cccccccccccccccccccccccccccccccc")
        assert response.status_code == 404
        assert "Key not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_invalid_hex_format(client):
    response = await client.delete("/invalid")
    assert response.status_code == 400
    assert "Invalid hex format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_bulk_put(client, mock_redis):
    with patch("app.main.redis_client", mock_redis):
        payload = {
            "11111111111111111111111111111111": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "22222222222222222222222222222222": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "33333333333333333333333333333333": "cccccccccccccccccccccccccccccccc",
        }
        response = await client.post("/bulk", json=payload)
        assert response.status_code == 200
        assert response.json() == {"stored": 3}


@pytest.mark.asyncio
async def test_bulk_put_empty_payload(client):
    response = await client.post("/bulk", json={})
    assert response.status_code == 400
    assert "Empty payload" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_key_count(client, mock_redis):
    with patch("app.main.redis_client", mock_redis):
        mock_redis.set(
            "11111111111111111111111111111111", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        mock_redis.set(
            "22222222222222222222222222222222", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        )
        response = await client.get("/stats/count")
        assert response.status_code == 200
        assert response.json() == {"key_count": 2}


@pytest.mark.asyncio
async def test_get_pattern_count(client, mock_redis):
    with patch("app.main.redis_client", mock_redis):
        mock_redis.set(
            "11111111111111111111111111111111", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        mock_redis.set(
            "22222222222222222222222222222222", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        )
        mock_redis.set(
            "33333333333333333333333333333333", "cccccccccccccccccccccccccccccccc"
        )
        response = await client.get("/stats/count/*")
        assert response.status_code == 200
        assert response.json() == {"pattern": "*", "count": 3}


@pytest.mark.asyncio
async def test_get_redis_info(client):
    with patch("app.main.redis_client.info") as mock_info:
        mock_info.return_value = {"redis_version": "7.0.0", "uptime_in_seconds": 1000}
        response = await client.get("/stats/info")
        assert response.status_code == 200
        assert response.json() == {"redis_version": "7.0.0", "uptime_in_seconds": 1000}


@pytest.mark.asyncio
async def test_get_redis_info_with_section(client):
    with patch("app.main.redis_client.info") as mock_info:
        mock_info.return_value = {"used_memory": 1000000}
        response = await client.get("/stats/info?section=memory")
        assert response.status_code == 200
        assert response.json() == {"used_memory": 1000000}


@pytest.mark.asyncio
async def test_get_memory_stats(client):
    with patch("app.main.redis_client.info") as mock_info:
        mock_info.return_value = {
            "used_memory": 1000000,
            "used_memory_human": "1M",
            "used_memory_peak": 2000000,
            "used_memory_peak_human": "2M",
            "used_memory_rss": 1200000,
            "maxmemory": 0,
            "maxmemory_human": "0B",
            "maxmemory_policy": "noeviction",
            "db0": {"keys": 5, "expires": 0},
        }
        response = await client.get("/stats/memory")
        assert response.status_code == 200
        data = response.json()
        assert "used_memory" in data
        assert data["key_count"] == 5


@pytest.mark.asyncio
async def test_get_operation_stats(client):
    with patch("app.main.redis_client.info") as mock_info:
        mock_info.return_value = {
            "total_connections_received": 50,
            "total_commands_processed": 500,
            "instantaneous_ops_per_sec": 10,
            "total_net_input_bytes": 25000,
            "total_net_output_bytes": 25000,
            "keyspace_hits": 400,
            "keyspace_misses": 100,
        }
        response = await client.get("/stats/operations")
        assert response.status_code == 200
        data = response.json()
        assert "total_commands_processed" in data
        assert data["hit_rate"] == round((400 / (400 + 100)) * 100, 2)


@pytest.mark.asyncio
async def test_get_all_stats(client):
    """Test /stats endpoint with minimal mocking"""

    # Mock the info method to return different data based on the section parameter
    def mock_info_side_effect(section=None):
        base_info = {
            "redis_version": "7.0.0",
            "uptime_in_seconds": 1000,
            "uptime_in_days": 0,
            "connected_clients": 1,
            "blocked_clients": 0,
            "used_memory": 1000000,
            "used_memory_human": "1M",
            "used_memory_peak": 2000000,
            "used_memory_peak_human": "2M",
            "used_memory_rss": 1200000,
            "maxmemory": 0,
            "maxmemory_human": "0B",
            "maxmemory_policy": "noeviction",
            "mem_fragmentation_ratio": 1.2,
            "total_connections_received": 10,
            "total_commands_processed": 100,
            "instantaneous_ops_per_sec": 5,
            "total_net_input_bytes": 5000,
            "total_net_output_bytes": 5000,
            "keyspace_hits": 80,
            "keyspace_misses": 20,
            "server_time_usec": 1234567890,
            "db0": {"keys": 3, "expires": 0},
        }
        return base_info

    with patch("app.main.redis_client.info") as mock_info, patch(
        "app.main.redis_client.dbsize"
    ) as mock_dbsize, patch("app.main.redis_client.scan_iter") as mock_scan:
        mock_info.side_effect = mock_info_side_effect
        mock_dbsize.return_value = 3
        mock_scan.return_value = iter([])

        response = await client.get("/stats")
        print(f"Response: {response.status_code} {response.json()}")
        assert response.status_code == 200
        data = response.json()
        assert "server" in data
        assert "memory" in data
        assert "keys" in data
        assert "operations" in data


@pytest.mark.asyncio
async def test_endpoints_redis_unavailable(client):
    """Test that endpoints return 503 when Redis is unavailable"""
    import redis

    # Test PUT endpoint
    with patch("app.main.redis_client.set") as mock_set:
        mock_set.side_effect = redis.exceptions.RedisError("Connection failed")
        response = await client.put(
            "/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            content="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        )
        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        assert "Redis unavailable" in response.json()["detail"]

    # Test GET endpoint
    with patch("app.main.redis_client.get") as mock_get:
        mock_get.side_effect = redis.exceptions.RedisError("Connection failed")
        response = await client.get("/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        assert response.status_code == 503
        assert "Redis unavailable" in response.json()["detail"]

    # Test DELETE endpoint
    with patch("app.main.redis_client.exists") as mock_exists:
        mock_exists.side_effect = redis.exceptions.RedisError("Connection failed")
        response = await client.delete("/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        assert response.status_code == 503
        assert "Redis unavailable" in response.json()["detail"]

    # Test bulk endpoint
    with patch("app.main.redis_client.pipeline") as mock_pipeline:
        mock_pipe = MagicMock()
        mock_pipeline.return_value = mock_pipe
        mock_pipe.execute.side_effect = redis.exceptions.RedisError("Connection failed")
        response = await client.post(
            "/bulk",
            json={
                "11111111111111111111111111111111": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            },
        )
        assert response.status_code == 503
        assert "Redis unavailable" in response.json()["detail"]

    # Test stats/info endpoint
    with patch("app.main.redis_client.info") as mock_info:
        mock_info.side_effect = redis.exceptions.RedisError("Connection failed")
        response = await client.get("/stats/info")
        assert response.status_code == 503
        assert "Redis unavailable" in response.json()["detail"]

    # Test stats/count endpoint
    with patch("app.main.redis_client.dbsize") as mock_dbsize:
        mock_dbsize.side_effect = redis.exceptions.RedisError("Connection failed")
        response = await client.get("/stats/count")
        assert response.status_code == 503
        assert "Redis unavailable" in response.json()["detail"]

    # Test /stats endpoint
    with patch("app.main.redis_client.info") as mock_info:
        mock_info.side_effect = redis.exceptions.RedisError("Connection failed")
        response = await client.get("/stats")
        assert response.status_code == 503
        assert "Redis unavailable" in response.json()["detail"]
