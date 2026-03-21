import json
import redis
from shared.config import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True
)


def get_cache(key):
    value = redis_client.get(key)
    return json.loads(value) if value else None


def set_cache(key, value, ttl=300):  # 5 min TTL
    redis_client.setex(key, ttl, json.dumps(value))