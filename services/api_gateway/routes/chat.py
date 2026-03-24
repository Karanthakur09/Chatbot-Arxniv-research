# from fastapi import APIRouter, Request
# from pydantic import BaseModel
# import time

# from shared.logging import get_logger
# from shared.cache import get_cache, set_cache

# from services.api_gateway.services.embedder import embed_query_cached
# from services.api_gateway.services.retriever import search_vectors, build_filters
# from services.api_gateway.services.reranker import rerank
# from services.api_gateway.services.context_builder import ContextBuilder
# from services.api_gateway.services.llm_gateway import LLMGateway
# from services.api_gateway.services.validators import QueryValidator
# from shared.rate_limiter import RateLimiter
# from services.api_gateway.services.memory import ConversationMemory

# logger = get_logger(__name__)

# router = APIRouter()

# context_builder = ContextBuilder()
# llm_gateway = LLMGateway()
# validator = QueryValidator()
# rate_limiter = RateLimiter()
# memory = ConversationMemory()


# # --- Helper Functions ---

# def diversify_results(results, max_per_doc=2):
#     doc_count = {}
#     diversified = []

#     for r in results:
#         doc_id = r.get("doc_id")

#         if doc_count.get(doc_id, 0) >= max_per_doc:
#             continue

#         doc_count[doc_id] = doc_count.get(doc_id, 0) + 1
#         diversified.append(r)

#     return diversified


# def deduplicate_results(results):
#     seen = set()
#     unique = []

#     for r in results:
#         content = r.get("content", "")
#         key = content[:200].strip()

#         if key in seen or not key:
#             continue

#         seen.add(key)
#         unique.append(r)

#     return unique


# # --- Models ---

# class ChatRequest(BaseModel):
#     query: str
#     session_id: str
#     top_k: int = 5
#     source: str | None = None
#     chunk_type: str | None = None


# # --- Main Route ---

# @router.post("/chat")
# def chat(req: ChatRequest, request: Request):

#     start_time = time.time()

#     # 1. Rate Limiting
#     client_ip = request.client.host
#     if not rate_limiter.allow(f"rate:{client_ip}"):
#         return {
#             "query": req.query,
#             "answer": "Too many requests. Please try again in a minute.",
#             "sources": []
#         }

#     # 2. Validation
#     is_valid, validated_query_or_error = validator.validate(req.query)
#     if not is_valid:
#         return {
#             "query": req.query,
#             "answer": validated_query_or_error,
#             "sources": []
#         }

#     query = validated_query_or_error

#     try:
#         # 3. Fetch Memory FIRST (important)
#         history = memory.get_history(req.session_id)

#         # 🔥 Limit history (avoid token explosion)
#         history = history[-3:] if history else []

#         # 🔥 Disable cache if conversation exists
#         use_cache = not history

#         if use_cache:
#             cache_key = f"chat:{query}:{req.source}:{req.chunk_type}"
#             cached = get_cache(cache_key)

#             if cached:
#                 logger.info("cache_hit=true")
#                 return cached

#         logger.info("cache_hit=false")

#         # 4. Retrieval
#         retrieval_start = time.time()

#         query_vector = embed_query_cached(query)

#         filters = build_filters(
#             source=req.source,
#             chunk_type=req.chunk_type
#         )

#         results = search_vectors(
#             query_vector,
#             query_text=query,
#             top_k=20,
#             filters=filters
#         )

#         if not results:
#             return {
#                 "query": query,
#                 "answer": "No relevant docs found.",
#                 "sources": []
#             }

#         retrieval_time = round(time.time() - retrieval_start, 3)
#         logger.info(f"retrieval_time={retrieval_time}s results={len(results)}")

#         # 5. Rerank
#         rerank_start = time.time()
        
#         if len(results) > 5:
#             logger.info(f"Reranking {len(results)} results...")
#             results = rerank(query, results, top_k=req.top_k)
#         else:
#             logger.info("Skipping rerank (too few results)")
#             results = results[:req.top_k]

#         rerank_time = round(time.time() - rerank_start, 3)
#         logger.info(f"rerank_time={rerank_time}s")

#         # 6. Clean Results
#         results = deduplicate_results(results)
#         results = diversify_results(results, max_per_doc=2)

#         results = results[:req.top_k]

#         # 7. Context
#         context = context_builder.build(results)

#         if not context or len(context.strip()) < 20:
#             return {
#                 "query": query,
#                 "answer": "Not found in context",
#                 "sources": results
#             }

#         # 8. LLM
#         llm_start = time.time()

#         answer = llm_gateway.generate_answer(
#             query=query,
#             context=context,
#             history=history
#         )

#         llm_time = round(time.time() - llm_start, 3)

#         total_time = round(time.time() - start_time, 3)

#         logger.info(
#             f"query='{query}' total_time={total_time}s llm_time={llm_time}s"
#         )

#         response = {
#             "query": query,
#             "answer": answer,
#             "sources": results,
#             "latency": total_time
#         }

#         # 9. Save Memory (ONLY meaningful answers)
#         if answer and answer != "Not found in context" and "[" in answer:
#             memory.save(req.session_id, query, answer)

#         # 10. Cache ONLY if stateless
#         if use_cache:
#             set_cache(cache_key, response, ttl=60)

#         return response

#     except Exception as e:
#         logger.error(f"chat_pipeline_failed query='{query}' error={e}")
#         return {
#             "query": query,
#             "answer": "Internal server error.",
#             "sources": []
#         }

#  imp code above don't delete it

from fastapi import APIRouter, Request
from pydantic import BaseModel
import time

from core.chat.chat_service import ChatService

from infra.ai.embeddings.local_embedder import LocalEmbedder
from infra.vector_db.qdrant_retriever import QdrantRetriever
from infra.ai.reranker.cross_encoder_reranker import CrossEncoderReranker
from infra.ai.llm.gateway_llm import GatewayLLM
from infra.cache.memory_adapter import MemoryAdapter

from core.chat.context_builder import ContextBuilder
from core.chat.validator import QueryValidator

from shared.logging import get_logger
from shared.cache import get_cache, set_cache
from shared.rate_limiter import RateLimiter

logger = get_logger(__name__)
router = APIRouter()


# ---------------------------
# Models
# ---------------------------

class ChatRequest(BaseModel):
    query: str
    session_id: str
    top_k: int = 5
    source: str | None = None
    chunk_type: str | None = None


# ---------------------------
# Dependencies
# ---------------------------

embedder = LocalEmbedder()
retriever = QdrantRetriever()
reranker = CrossEncoderReranker()
llm = GatewayLLM()
memory = MemoryAdapter()
context_builder = ContextBuilder()

chat_service = ChatService(
    embedder=embedder,
    retriever=retriever,
    reranker=reranker,
    context_builder=context_builder,
    llm=llm,
    memory=memory
)

validator = QueryValidator()
rate_limiter = RateLimiter()


# ---------------------------
# Route
# ---------------------------

@router.post("/chat")
def chat(req: ChatRequest, request: Request):

    start_time = time.time()

    # 1. Rate limiting
    client_ip = request.client.host
    if not rate_limiter.allow(f"rate:{client_ip}"):
        return {
            "query": req.query,
            "answer": "Too many requests. Please try again in a minute.",
            "sources": []
        }

    # 2. Validation
    is_valid, validated_query_or_error = validator.validate(req.query)
    if not is_valid:
        return {
            "query": req.query,
            "answer": validated_query_or_error,
            "sources": []
        }

    query = validated_query_or_error

    try:
        # 3. Cache (only for stateless queries)
        cache_key = f"chat:{query}:{req.source}:{req.chunk_type}"
        cached = get_cache(cache_key)

        if cached:
            logger.info("cache_hit=true")
            return cached

        logger.info("cache_hit=false")

        # 4. Core Chat Logic
        response = chat_service.handle_chat(req)

        total_time = round(time.time() - start_time, 3)
        response["latency"] = total_time

        logger.info(f"query='{query}' total_time={total_time}s")

        # 5. Cache response
        if response.get("answer") and response["answer"] != "Not found in context":
            set_cache(cache_key, response, ttl=60)

        return response

    except Exception as e:
        logger.error(f"chat_route_failed query='{query}' error={e}")
        return {
            "query": query,
            "answer": "Internal server error.",
            "sources": []
        }