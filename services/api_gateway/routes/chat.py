from fastapi import APIRouter, Request
from pydantic import BaseModel
import time

from shared.logging import get_logger
from shared.cache import get_cache, set_cache

from services.api_gateway.services.embedder import embed_query_cached
from services.api_gateway.services.retriever import search_vectors, build_filters
from services.api_gateway.services.reranker import rerank
from services.api_gateway.services.context_builder import ContextBuilder
from services.api_gateway.services.llm_gateway import LLMGateway
from services.api_gateway.services.validators import QueryValidator
from shared.rate_limiter import RateLimiter

logger = get_logger(__name__)

router = APIRouter()

context_builder = ContextBuilder()
llm_gateway = LLMGateway()
validator = QueryValidator()
rate_limiter = RateLimiter()


def diversify_results(results, max_per_doc=2):

    doc_count = {}
    diversified = []

    for r in results:
        doc_id = r.get("doc_id")

        if doc_count.get(doc_id, 0) >= max_per_doc:
            continue

        doc_count[doc_id] = doc_count.get(doc_id, 0) + 1
        diversified.append(r)

    return diversified

def deduplicate_results(results):
    """Removes duplicate or near-duplicate chunks based on the first 200 characters."""
    seen = set()
    unique = []

    for r in results:
        # Get the text content of the chunk
        content = r.get("content", "")
        # Create a 'fingerprint' of the first 200 chars to identify duplicates
        key = content[:200].strip()

        if key in seen or not key:
            continue

        seen.add(key)
        unique.append(r)

    return unique


class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    source: str | None = None
    chunk_type: str | None = None

@router.post("/chat")
def chat(req: ChatRequest, request: Request):
    
    # Rate limiter
    client_ip = request.client.host 
    if not rate_limiter.allow(f"rate:{client_ip}"):
        logger.warning(f"rate_limit_exceeded ip={client_ip}")
        return {
            "query": req.query,
            "answer": "Too many requests. Please try again in a minute.",
            "sources": []
        }
        
    # 1. Validate First
    is_valid, validated_query_or_error = validator.validate(req.query)
    
    if not is_valid:
        logger.warning(f"validation_failed query='{req.query}' reason='{validated_query_or_error}'")
        return {
            "query": req.query,
            "answer": validated_query_or_error,
            "sources": []
        }
        
    # Use the cleaned query from here on
    query = validated_query_or_error
    retrieval_start = time.time()

    # 2. Cache Check (Use cleaned query in key)
    cache_key = f"chat:{query}:{req.source}:{req.chunk_type}"
    cached = get_cache(cache_key)
    
    if cached:
        logger.info("cache_hit=true")
        return cached
    
    logger.info("cache_hit=false")   
    
    try:
        # Step 1: Embed
        query_vector = embed_query_cached(query)

        # Step 2: Filters
        filters = build_filters(
            source=req.source,
            chunk_type=req.chunk_type
        )

        # Step 3: Retrieve
        results = search_vectors(
            query_vector,
            query_text=query,
            top_k=15,
            filters=filters
        )
        
        if not results:
            return {
                "query": query,
                "answer": "No relevant documents found.",
                "sources": []
            }
        
        retrieval_time = round(time.time() - retrieval_start, 3)
        logger.info(f"retrieval_time={retrieval_time}s results={len(results)}")
        
        # Step 4: Rerank
        rerank_start = time.time()
        results = rerank(query, results, top_k=req.top_k)
        rerank_time = round(time.time() - rerank_start, 3)
        logger.info(f"rerank_time={rerank_time}s top_k={len(results)}")
        
        #NEW STEP 4.5: Deduplicate
        # This cleans the results so the LLM doesn't read the same thing twice
        results = deduplicate_results(results)
        
        logger.info(f"after_deduplication results={len(results)}")
        
        # 4.75 Diversify (Make sure we don't have too many chunks from the same PDF)
        results = diversify_results(results, max_per_doc=3)
        
        # 4. Final Crop (Keep only the top_k after cleaning)
        results = results[:req.top_k]
        
        # Step 5: Context
        context = context_builder.build(results)
        if not context or len(context.strip()) < 20:
            return {
                "query": query,
                "answer": "Not found in context",
                "sources": results
            }
            
        # Step 6: LLM
        llm_start = time.time()
        answer = llm_gateway.generate_answer(query, context)
        llm_time = round(time.time() - llm_start, 3)
        
        total_time = round(time.time() - retrieval_start, 3)
        
        response = {
            "query": query,
            "answer": answer,
            "sources": results,
            "latency": total_time
        }
        
        logger.info(f"query='{query}' total_time={total_time}s llm_time={llm_time}s")
        
        # Cache response
        set_cache(cache_key, response, ttl=60)

        return response

    except Exception as e:
        logger.error(f"chat_pipeline_failed query='{query}' error={e}")
        return {
            "query": query,
            "answer": "Internal server error.",
            "sources": []
        }