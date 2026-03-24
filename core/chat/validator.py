import re

from shared.logging import get_logger

logger = get_logger(__name__)


class QueryValidator:

    def __init__(self, min_len=3, max_len=500):
        self.min_len = min_len
        self.max_len = max_len

    def validate(self, query: str):

        if not query:
            return False, "Query is empty"

        query = query.strip()

        if len(query) < self.min_len:
            return False, "Query too short"

        if len(query) > self.max_len:
            return False, "Query too long"

        # 🔥 basic prompt injection detection
        if self._is_malicious(query):
            logger.warning(f"Potential prompt injection: {query}")
            return False, "Invalid query"

        return True, query

    def _is_malicious(self, query: str) -> bool:

        patterns = [
            r"ignore previous instructions",
            r"system prompt",
            r"you are chatgpt",
            r"act as",
            r"bypass",
        ]

        query_lower = query.lower()

        return any(re.search(p, query_lower) for p in patterns)