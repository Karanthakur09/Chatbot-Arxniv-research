import json

from shared.redis_client import get_redis_client
from shared.logging import get_logger

logger = get_logger(__name__)


class ConversationMemory:

    def __init__(self, ttl=3600):
        self.ttl = ttl

    async def get_history(self, session_id: str):
        """Async get history from Redis"""
        try:
            redis_client = await get_redis_client()
            data = await redis_client.get(f"chat:{session_id}")
            return json.loads(data) if data else []
        except Exception as e:
            logger.error(f"Memory read error: {e}")
            return []

    async def save(self, session_id: str, query: str, answer: str):
        """Async save history to Redis"""
        try:
            history = await self.get_history(session_id)

            history.append({
                "query": query,
                "answer": answer
            })

            # keep last 5 turns
            history = history[-5:]

            redis_client = await get_redis_client()
            await redis_client.setex(
                f"chat:{session_id}",
                self.ttl,
                json.dumps(history)
            )

        except Exception as e:
            logger.error(f"Memory write error: {e}")