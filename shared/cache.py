import json
from shared.redis_client import get_redis_client
from shared.config import settings

async def get_cache(key):
    """Async get from cache"""
    redis_client = await get_redis_client()
    value = await redis_client.get(key)
    return json.loads(value) if value else None


async def set_cache(key, value, ttl=300):  # 5 min TTL
    """Async set in cache with TTL"""
    redis_client = await get_redis_client()
    await redis_client.setex(key, ttl, json.dumps(value))