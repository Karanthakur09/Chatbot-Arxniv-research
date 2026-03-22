import redis
from shared.config import settings

# This creates a single instance that other files will share
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True
)

def get_redis_client():
    """Helper function to return the shared client"""
    return redis_client
