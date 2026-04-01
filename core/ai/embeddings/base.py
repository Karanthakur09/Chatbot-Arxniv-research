from abc import ABC, abstractmethod
from typing import List


class BaseEmbedder(ABC):
    """
    Interface for embedding providers (Async)
    """

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """
        Convert text into vector embedding (async)
        """
        pass