from fastapi import APIRouter
from pydantic import BaseModel
import time

from shared.logging import get_logger
from shared.cache import get_cache, set_cache

from services.api_gateway.services.embedder import embed_query_cached
from services.api_gateway.services.retriever import search_vectors, build_filters
from services.api_gateway.services.reranker import rerank
from services.api_gateway.services.context_builder import ContextBuilder
from services.api_gateway.services.llm_gateway import LLMGateway

logger = get_logger(__name__)

router = APIRouter()

context_builder = ContextBuilder()
llm_gateway = LLMGateway()

class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    source: str | None = None
    chunk_type: str | None = None


@router.post("/chat")
def chat(req: ChatRequest):

    retrieval_start = time.time()

    # ✅ Cache (same pattern as search)
    cache_key = f"chat:{req.query}:{req.source}:{req.chunk_type}"
    cached = get_cache(cache_key)
    
    if cached:
        logger.info("cache_hit=true")
        return cached
    else:
        logger.info("cache_hit=false")   
    
    try:
        # Step 1: Embed
        query_vector = embed_query_cached(req.query)

        # Step 2: Filters
        filters = build_filters(
            source=req.source,
            chunk_type=req.chunk_type
        )

        # Step 3: Retrieve (bigger pool)
        results = search_vectors(
            query_vector,
            query_text=req.query,
            top_k=15,
            filters=filters
        )
        
        if not results:
            return {
                "query": req.query,
                "answer": "No relevant documents found.",
                "sources": []
            }
        
        retrieval_time = round(time.time() - retrieval_start, 3)
        logger.info(f"retrieval_time={retrieval_time}s results={len(results)}")
        
        rerank_start = time.time()
        
        # Step 4: Rerank
        results = rerank(
            req.query,
            results,
            top_k=req.top_k
        )
        
        rerank_time = round(time.time() - rerank_start, 3)
        logger.info(f"rerank_time={rerank_time}s top_k={len(results)}")
        
        # Step 5: Context
        context = context_builder.build(results)

        if not context or len(context.strip()) < 20:
            return {
                "query": req.query,
                "answer": "Not found in context",
                "sources": results
            }
            
        context_length = len(context)
        logger.info(f"context_length={context_length}")
        
        llm_start = time.time()
        # Step 6: LLM
        answer = llm_gateway.generate_answer(req.query, context)
        
        llm_time = round(time.time() - llm_start, 3)
        logger.info(f"llm_time={llm_time}s")
        
        response = {
            "query": req.query,
            "answer": answer,
            "sources": results,
            "latency": round(time.time() - retrieval_start, 2) 
        }
        
        total_time = round(time.time() - retrieval_start, 3)
        logger.info(
            f"query='{req.query}' total_time={total_time}s"
        )
        
        # Cache response
        set_cache(cache_key, response, ttl=60)

        return response

    except Exception as e:
        logger.error(f"chat_pipeline_failed query='{req.query}' error={e}")

        return {
            "query": req.query,
            "answer": "Internal server error.",
            "sources": []
        }