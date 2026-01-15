import os
import re

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
