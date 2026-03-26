# from typing import List, Dict

# from infra.cache.memory import ConversationMemory
# from shared.logging import get_logger

# logger = get_logger(__name__)


# class MemoryAdapter:
#     """
#     Adapter for conversation memory.

#     Currently uses Redis (ConversationMemory),
#     but can be swapped with DB-based memory later.
#     """

#     def __init__(self):
#         self.backend = ConversationMemory()

#     def get_history(self, session_id: str) -> List[Dict]:
#         try:
#             return self.backend.get_history(session_id)
#         except Exception as e:
#             logger.error(f"memory_get_failed session_id='{session_id}' error={e}")
#             return []

#     def save(self, session_id: str, query: str, answer: str):
#         try:
#             self.backend.save(session_id, query, answer)
#         except Exception as e:
#             logger.error(f"memory_save_failed session_id='{session_id}' error={e}")


from typing import List, Dict

from infra.cache.memory import ConversationMemory
from infra.db.session import SessionLocal
from infra.db.repositories.chat_repository import ChatRepository

from shared.logging import get_logger

logger = get_logger(__name__)


class MemoryAdapter:
    """
    Hybrid Memory:
    - Redis → fast recent memory
    - PostgreSQL → persistent history
    """

    def __init__(self):
        self.redis_memory = ConversationMemory()

    def get_history(self, session_id: str) -> List[Dict]:

        # 1. Try Redis first
        try:
            history = self.redis_memory.get_history(session_id)
            if history:
                return history
        except Exception as e:
            logger.error(f"redis_memory_failed session_id='{session_id}' error={e}")

        # 2. Fallback to PostgreSQL
        try:
            db = SessionLocal()
            repo = ChatRepository(db)

            history = repo.get_last_messages(session_id, limit=5)

            db.close()
            return history

        except Exception as e:
            logger.error(f"db_memory_failed session_id='{session_id}' error={e}")
            return []

    def save(self, session_id: str, query: str, answer: str):

        # 1. Save to Redis
        try:
            self.redis_memory.save(session_id, query, answer)
        except Exception as e:
            logger.error(f"redis_save_failed session_id='{session_id}' error={e}")

        # 2. Save to PostgreSQL
        try:
            db = SessionLocal()
            repo = ChatRepository(db)

            repo.save_message(session_id, "user", query)
            repo.save_message(session_id, "assistant", answer)

            db.close()

        except Exception as e:
            logger.error(f"db_save_failed session_id='{session_id}' error={e}")