from typing import List

from sentence_transformers import SentenceTransformer

from shared.cache import get_cache, set_cache
from shared.logging import get_logger

logger = get_logger(__name__)


class LocalEmbedder:
    """
    Production embedding wrapper (no global model)
    """

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed(self, text: str) -> List[float]:

        cache_key = f"embed:{text}"

        cached = get_cache(cache_key)
        if cached:
            return cached

        try:
            vector = self.model.encode(text).tolist()
            set_cache(cache_key, vector, ttl=3600)
            return vector

        except Exception as e:
            logger.error(f"embedding_failed text='{text}' error={e}")
            return []