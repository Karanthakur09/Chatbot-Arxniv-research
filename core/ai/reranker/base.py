from abc import ABC, abstractmethod
from typing import List, Dict


class BaseReranker(ABC):
    """
    Interface for reranking models (Async)
    """

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """
        Rerank retrieved results (async)
        """
        pass