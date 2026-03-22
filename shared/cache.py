import json
from shared.redis_client import get_redis_client
from shared.config import settings

# Get the shared instance
redis_client = get_redis_client()

def get_cache(key):
    value = redis_client.get(key)
    return json.loads(value) if value else None


def set_cache(key, value, ttl=300):  # 5 min TTL
    redis_client.setex(key, ttl, json.dumps(value))