from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseRetriever(ABC):
    """
    Interface for retrieval systems (vector + hybrid) - Async
    """

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        query_text: str,
        top_k: int = 10,
        source: Optional[str] = None,
        chunk_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve relevant documents (async)
        """
        pass