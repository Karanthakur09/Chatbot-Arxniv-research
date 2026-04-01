from typing import List
import asyncio

from sentence_transformers import SentenceTransformer

from shared.cache import get_cache, set_cache
from shared.logging import get_logger

logger = get_logger(__name__)


class LocalEmbedder:
    """
    Production embedding wrapper (async) - no global model
    """

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    async def embed(self, text: str) -> List[float]:
        """Async embed text with caching"""
        cache_key = f"embed:{text}"

        cached = await get_cache(cache_key)
        if cached:
            return cached

        try:
            # Run CPU-intensive operation in thread pool
            vector = await asyncio.to_thread(
                lambda: self.model.encode(text).tolist()
            )
            await set_cache(cache_key, vector, ttl=3600)
            return vector

        except Exception as e:
            logger.error(f"embedding_failed text='{text}' error={e}")
            return []