from typing import List, Dict

from infra.cache.memory import ConversationMemory
from infra.db.session import AsyncSessionLocal 
from infra.db.repositories.chat_repository import ChatRepository

from shared.logging import get_logger

logger = get_logger(__name__)

class MemoryAdapter:
    """
    Hybrid Memory (Async Version):
    - Redis → fast recent memory
    - PostgreSQL → persistent async history
    """

    def __init__(self):
        self.redis_memory = ConversationMemory()

    async def get_history(self, session_id: str) -> List[Dict]:
        """Async get history from Redis first, then DB fallback"""
        # 1. Try Redis first
        try:
            history = await self.redis_memory.get_history(session_id)
            if history:
                return history
        except Exception as e:
            logger.error(f"redis_memory_failed session_id='{session_id}' error={e}")

        # 2. Fallback to PostgreSQL
        try:
            async with AsyncSessionLocal() as db:
                repo = ChatRepository(db)
                history = await repo.get_messages(session_id, limit=5)
                return history

        except Exception as e:
            logger.error(f"db_memory_failed session_id='{session_id}' error={e}")
            return []

    async def save(self, session_id: str, query: str, answer: str):
        """Async save history to Redis and DB"""
        # 1. Save to Redis
        try:
            await self.redis_memory.save(session_id, query, answer)
        except Exception as e:
            logger.error(f"redis_save_failed session_id='{session_id}' error={e}")

        # 2. Save to PostgreSQL
        try:
            async with AsyncSessionLocal() as db:
                repo = ChatRepository(db)
                await repo.save_message(session_id, "user", query)
                await repo.save_message(session_id, "assistant", answer)

        except Exception as e:
            logger.error(f"db_save_failed session_id='{session_id}' error={e}")
