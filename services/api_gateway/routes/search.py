from fastapi import APIRouter
from pydantic import BaseModel

from services.api_gateway.services.embedder import embed_query
from services.api_gateway.services.retriever import (
    search_vectors,
    build_filters
)
from services.api_gateway.services.reranker import rerank
from shared.cache import get_cache, set_cache

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    source: str | None = None
    chunk_type: str | None = None


@router.post("/search")
def search(req: SearchRequest):
    
    # cache mechanism
    cache_key = f"search:{req.query}:{req.source}:{req.chunk_type}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    # Step 1: Embed query
    query_vector = embed_query(req.query)

    # Step 2: Build filters (hybrid)
    filters = build_filters(
        source=req.source,
        chunk_type=req.chunk_type
    )

    # Step 3: Vector search (bigger pool for reranking)
    results = search_vectors(
        query_vector,
        query_text=req.query,
        top_k=15,
        filters=filters
    )

    # Step 4: Rerank
    final_results = rerank(
        req.query,
        results,
        top_k=req.top_k
    )

    # return {
    #     "query": req.query,
    #     "results": final_results
    # }
    
    response = {
        "query": req.query,
        "results": final_results
    }

    set_cache(cache_key, response, ttl=120)  # short cache

    return response