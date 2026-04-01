from abc import ABC, abstractmethod
from typing import List, Dict


class BaseLLM(ABC):
    """
    Interface for LLM providers (Async)
    """

    @abstractmethod
    async def generate_answer(
        self,
        query: str,
        context: str,
        history: List[Dict]
    ) -> str:
        """
        Generate answer using context + history (async)
        """
        pass