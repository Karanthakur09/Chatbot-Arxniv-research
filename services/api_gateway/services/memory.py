import json

from shared.cache import get_redis_client
from shared.logging import get_logger

logger = get_logger(__name__)


class ConversationMemory:

    def __init__(self, ttl=3600):
        self.redis = get_redis_client()
        self.ttl = ttl

    def get_history(self, session_id: str):

        try:
            data = self.redis.get(f"chat:{session_id}")
            return json.loads(data) if data else []
        except Exception as e:
            logger.error(f"Memory read error: {e}")
            return []

    def save(self, session_id: str, query: str, answer: str):

        try:
            history = self.get_history(session_id)

            history.append({
                "query": query,
                "answer": answer
            })

            # keep last 5 turns
            history = history[-5:]

            self.redis.setex(
                f"chat:{session_id}",
                self.ttl,
                json.dumps(history)
            )

        except Exception as e:
            logger.error(f"Memory write error: {e}")