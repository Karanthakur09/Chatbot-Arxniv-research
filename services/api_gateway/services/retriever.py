from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from services.api_gateway.services.keyword_matcher import keyword_score
from shared.config import settings

client = QdrantClient(
    host=settings.QDRANT_HOST,
    port=settings.QDRANT_PORT
)

COLLECTION_NAME = "documents"


# Build Filters (Hybrid Search)
def build_filters(source=None, chunk_type=None):

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

    if conditions:
        return Filter(must=conditions)

    return None


# Hybrid vector search
def search_vectors(query_vector, query_text, top_k=20, filters=None):

    search_result = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
        query_filter=filters
    )

    results = []

    for hit in search_result.points:
        payload = hit.payload or {}

        content = payload.get("content", "")

        # keyword score
        k_score = keyword_score(query_text, content)

        # hybrid score (weighted)
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

    # sort by hybrid score
    results.sort(key=lambda x: x["hybrid_score"], reverse=True)

    return results