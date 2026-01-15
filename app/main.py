import os
import re
from typing import Optional

import redis
from fastapi import FastAPI, HTTPException, Request, Response

HEX_128_RE = re.compile(r"^[A-Fa-f0-9]{32}$")

app = FastAPI()

# Get Redis password from environment (empty string becomes None)
redis_password = os.getenv("REDIS_PASSWORD")
redis_password = redis_password if redis_password else None

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=redis_password,
    socket_timeout=1,
    decode_responses=True,
)


def normalize_hex(value: str) -> str:
    if not isinstance(value, str) or not HEX_128_RE.fullmatch(value):
        raise HTTPException(status_code=400, detail="Invalid hex format")
    return value.lower()


# ---------- Health Endpoint ----------


@app.get("/health")
async def health():
    try:
        redis_client.ping()
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    return {"status": "ok"}


# ---------- Bulk Endpoint ----------


@app.post("/bulk")
async def bulk_put(payload: dict):
    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")

    pipe = redis_client.pipeline()

    try:
        for raw_key, raw_value in payload.items():
            key = normalize_hex(raw_key)
            value = normalize_hex(raw_value)
            pipe.set(key, value)

        pipe.execute()
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    return {"stored": len(payload)}


# ---------- Statistics Endpoints ----------


@app.get("/stats/count")
async def get_key_count():
    """Get total number of keys in the database."""
    try:
        count = redis_client.dbsize()  # Returns total keys in current database
        return {"key_count": count}
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")


@app.get("/stats/count/{pattern}")
async def get_pattern_count(pattern: str = "*"):
    """
    Count keys matching a pattern.
    Pattern examples: "*", "prefix:*", "a?c*"
    """
    try:
        count = 0
        # Use SCAN for better performance with large databases
        for _ in redis_client.scan_iter(match=pattern):
            count += 1
        return {"pattern": pattern, "count": count}
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")


@app.get("/stats/info")
async def get_redis_info(section: Optional[str] = None):
    """
    Get Redis server information.
    Optional section: server, clients, memory, persistence, stats, etc.
    """
    try:
        if section:
            info = redis_client.info(section=section)
        else:
            info = redis_client.info()
        return info
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")


@app.get("/stats/memory")
async def get_memory_stats():
    """Get memory usage statistics."""
    try:
        info = redis_client.info("memory")
        return {
            "used_memory": info.get("used_memory"),
            "used_memory_human": info.get("used_memory_human"),
            "used_memory_peak": info.get("used_memory_peak"),
            "used_memory_peak_human": info.get("used_memory_peak_human"),
            "used_memory_rss": info.get("used_memory_rss"),
            "maxmemory": info.get("maxmemory"),
            "maxmemory_human": info.get("maxmemory_human"),
            "maxmemory_policy": info.get("maxmemory_policy"),
            "key_count": info.get("db0", {}).get("keys", 0) if "db0" in info else 0,
        }
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")


@app.get("/stats/operations")
async def get_operation_stats():
    """Get operation statistics."""
    try:
        info = redis_client.info("stats")
        return {
            "total_connections_received": info.get("total_connections_received"),
            "total_commands_processed": info.get("total_commands_processed"),
            "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec"),
            "total_net_input_bytes": info.get("total_net_input_bytes"),
            "total_net_output_bytes": info.get("total_net_output_bytes"),
            "keyspace_hits": info.get("keyspace_hits"),
            "keyspace_misses": info.get("keyspace_misses"),
            "hit_rate": round(
                (
                    info.get("keyspace_hits", 0)
                    / max(
                        1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)
                    )
                )
                * 100,
                2,
            ),
        }
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")


@app.get("/stats")
async def get_all_stats():
    """Get comprehensive Redis statistics."""
    try:
        # Get multiple info sections
        general_info = redis_client.info()
        memory_info = redis_client.info("memory")
        stats_info = redis_client.info("stats")

        # Get key count
        total_keys = redis_client.dbsize()

        # Count keys with your hex pattern (optional)
        hex_keys_count = 0
        try:
            for _ in redis_client.scan_iter(match="*"):
                hex_keys_count += 1  # Since all your keys are hex, count all
        except redis.exceptions.RedisError:
            # If scan fails, estimate from dbsize
            hex_keys_count = total_keys

        return {
            "server": {
                "redis_version": general_info.get("redis_version"),
                "uptime_in_seconds": general_info.get("uptime_in_seconds"),
                "uptime_in_days": general_info.get("uptime_in_days"),
                "connected_clients": general_info.get("connected_clients"),
                "blocked_clients": general_info.get("blocked_clients"),
            },
            "memory": {
                "used_memory": memory_info.get("used_memory"),
                "used_memory_human": memory_info.get("used_memory_human"),
                "used_memory_peak": memory_info.get("used_memory_peak"),
                "used_memory_peak_human": memory_info.get("used_memory_peak_human"),
                "maxmemory": memory_info.get("maxmemory"),
                "maxmemory_human": memory_info.get("maxmemory_human"),
                "mem_fragmentation_ratio": memory_info.get("mem_fragmentation_ratio"),
            },
            "keys": {
                "total_keys": total_keys,
                "hex_keys_count": hex_keys_count,
                "keyspace_hits": stats_info.get("keyspace_hits"),
                "keyspace_misses": stats_info.get("keyspace_misses"),
                "hit_rate_percentage": round(
                    (
                        stats_info.get("keyspace_hits", 0)
                        / max(
                            1,
                            stats_info.get("keyspace_hits", 0)
                            + stats_info.get("keyspace_misses", 0),
                        )
                    )
                    * 100,
                    2,
                ),
            },
            "operations": {
                "total_commands_processed": stats_info.get("total_commands_processed"),
                "instantaneous_ops_per_sec": stats_info.get(
                    "instantaneous_ops_per_sec"
                ),
                "total_connections_received": stats_info.get(
                    "total_connections_received"
                ),
            },
            "timestamp": general_info.get("server_time_usec")
            or general_info.get("uptime_in_seconds"),
        }
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")


# ---------- Core Endpoints ----------


@app.put("/{key}")
async def put_value(key: str, request: Request):
    key = normalize_hex(key)
    body = (await request.body()).decode().strip()
    value = normalize_hex(body)

    try:
        redis_client.set(key, value)
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    return Response(status_code=201)


@app.get("/{key}")
async def get_value(key: str):
    key = normalize_hex(key)

    try:
        value = redis_client.get(key)
    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    if value is None:
        raise HTTPException(status_code=404, detail="Key not found")

    return value


@app.delete("/{key}")
async def delete_value(key: str):
    """
    Delete a key-value pair from Redis.

    Similar to PUT endpoint in terms of:
    1. Key validation using normalize_hex()
    2. Redis error handling
    3. Returns appropriate HTTP status codes

    Key differences:
    1. No request body needed (DELETE doesn't typically have a body)
    2. Returns 200 if key existed and was deleted
    3. Returns 404 if key didn't exist (matches GET behavior)
    """
    key = normalize_hex(key)

    try:
        # Check if key exists first (like GET does)
        exists = redis_client.exists(key)

        if not exists:
            raise HTTPException(status_code=404, detail="Key not found")

        # Delete the key
        deleted = redis_client.delete(key)

        # Should be 1 since we verified it exists
        if deleted != 1:
            raise HTTPException(status_code=500, detail="Failed to delete key")

    except redis.exceptions.RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable")

    return Response(status_code=200)
