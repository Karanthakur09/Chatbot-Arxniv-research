import redis.asyncio as redis
from shared.config import settings

# Async Redis connection pool
_redis_pool = None

async def get_redis_client():
    """Get or create async Redis client"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
            max_connections=10
        )
    return redis.Redis(connection_pool=_redis_pool)
