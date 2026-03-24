from typing import List, Dict

from infra.cache.memory import ConversationMemory
from shared.logging import get_logger

logger = get_logger(__name__)


class MemoryAdapter:
    """
    Adapter for conversation memory.

    Currently uses Redis (ConversationMemory),
    but can be swapped with DB-based memory later.
    """

    def __init__(self):
        self.backend = ConversationMemory()

    def get_history(self, session_id: str) -> List[Dict]:
        try:
            return self.backend.get_history(session_id)
        except Exception as e:
            logger.error(f"memory_get_failed session_id='{session_id}' error={e}")
            return []

    def save(self, session_id: str, query: str, answer: str):
        try:
            self.backend.save(session_id, query, answer)
        except Exception as e:
            logger.error(f"memory_save_failed session_id='{session_id}' error={e}")