from typing import List, Dict

from sentence_transformers import CrossEncoder

from shared.logging import get_logger

logger = get_logger(__name__)


class CrossEncoderReranker:
    """
    Production reranker (no global model)
    """

    def __init__(self):
        self.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def rerank(
        self,
        query: str,
        results: List[Dict],
        top_k: int
    ) -> List[Dict]:

        try:
            pairs = [(query, r["content"]) for r in results]
            scores = self.model.predict(pairs)

            for r, score in zip(results, scores):
                r["rerank_score"] = float(score)

            results.sort(key=lambda x: x["rerank_score"], reverse=True)

            return results[:top_k]

        except Exception as e:
            logger.error(f"rerank_failed query='{query}' error={e}")
            return results[:top_k]