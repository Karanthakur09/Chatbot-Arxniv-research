from typing import List, Dict, Optional
import asyncio

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from core.retrieval.keyword_matcher import keyword_score
from shared.config import settings
from shared.logging import get_logger

logger = get_logger(__name__)


class QdrantRetriever:
    """
    Production Qdrant retriever (async) - fully decoupled
    """

    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        self.collection_name = "documents"

    def _build_filters(self, source=None, chunk_type=None):

        conditions = []

        if source:
            conditions.append(
                FieldCondition(
                    key="source",
                    match=MatchValue(value=source)
                )
            )

        if chunk_type:
            conditions.append(
                FieldCondition(
                    key="type",
                    match=MatchValue(value=chunk_type)
                )
            )

        return Filter(must=conditions) if conditions else None

    async def search(
        self,
        query_vector: List[float],
        query_text: str,
        top_k: int = 10,
        source: Optional[str] = None,
        chunk_type: Optional[str] = None
    ) -> List[Dict]:
        """Async search in Qdrant using thread pool"""
        try:
            filters = self._build_filters(source, chunk_type)

            # Run blocking search in thread pool
            search_result = await asyncio.to_thread(
                lambda: self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=top_k,
                    query_filter=filters
                )
            )

            results = []

            for hit in search_result.points:
                payload = hit.payload or {}

                content = payload.get("content", "")

                k_score = keyword_score(query_text, content)
                final_score = (0.7 * hit.score) + (0.3 * k_score)

                results.append({
                    "doc_id": payload.get("doc_id"),
                    "content": content,
                    "type": payload.get("type"),
                    "source": payload.get("source"),
                    "vector_score": hit.score,
                    "keyword_score": k_score,
                    "hybrid_score": final_score
                })

            results.sort(key=lambda x: x["hybrid_score"], reverse=True)

            return results

        except Exception as e:
            logger.error(f"retrieval_failed query='{query_text}' error={e}")
            return []