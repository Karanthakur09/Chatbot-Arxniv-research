import time

from shared.cache import get_redis_client
from shared.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:

    def __init__(self, limit=30, window=60):
        self.limit = limit          # requests
        self.window = window        # seconds
        self.redis = get_redis_client()

    def allow(self, key: str) -> bool:

        try:
            current = self.redis.incr(key)

            if current == 1:
                self.redis.expire(key, self.window)

            if current > self.limit:
                return False

            return True

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return True  # fail open (important in prod)