from fastapi import APIRouter, Request, Depends
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
from services.api_gateway.dependencies.auth import get_current_user
from shared.logging import get_logger
from shared.cache import get_cache, set_cache
from shared.rate_limiter import RateLimiter
from fastapi.responses import StreamingResponse
import json
import hashlib
from fastapi.responses import JSONResponse
from infra.db.session import SessionLocal
from fastapi import BackgroundTasks # 1. Import BackgroundTasks
from infra.db.repositories.conversation_repository import ConversationRepository

logger = get_logger(__name__)
router = APIRouter()

# ---------------------------
# Models
# ---------------------------

class ChatRequest(BaseModel):
    query: str
    session_id: str
    conversation_id: str | None = None
    top_k: int = 5
    source: str | None = None
    chunk_type: str | None = None

# ---------------------------
# Helper Functions
# ---------------------------

def get_llm_cache_key(req: ChatRequest) -> str:
    """Generates a consistent, hashed cache key for both sync and stream."""
    clean_query = req.query.strip().lower()
    source = req.source or "all"
    chunk_type = req.chunk_type or "standard"
    
    # We include session_id only if answers are history-dependent
    # Otherwise, remove req.session_id for a global cache
    raw_key = f"{req.session_id}:{clean_query}:{source}:{chunk_type}"
    key_hash = hashlib.md5(raw_key.encode()).hexdigest()
    
    return f"llm_cache:{key_hash}"

# 4. The Background Worker Function
def finalize_chat_session(req: ChatRequest, full_answer: str, cache_key: str):
    """Runs after the stream is finished to persist data safely."""
    try:
        # Save to Redis Cache
        set_cache(cache_key, {"query": req.query, "answer": full_answer}, ttl=60)
        
        # Save to Postgres Memory/History
        # This ensures history is updated even if the user disconnected mid-stream
        chat_service.memory.save(req.session_id, req.query, full_answer)
        
        logger.info(f"background_save_complete session={req.session_id}")
    except Exception as e:
        logger.error(f"background_save_failed: {e}")

    
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
def chat(
    req: ChatRequest, 
    request: Request, 
    background_tasks: BackgroundTasks, 
    user_id: str = Depends(get_current_user)
):
    start_time = time.time()
    client_ip = request.client.host

    # 1. PRE-CHECK: Rate limiting
    if not rate_limiter.allow(f"rate:{client_ip}"):
        return JSONResponse(
            status_code=429,
            content={"query": req.query, "answer": "Too many requests.", "sources": []}
        )

    # 2. PRE-CHECK: Validation
    is_valid, validated_query = validator.validate(req.query)
    if not is_valid:
        return {"query": req.query, "answer": validated_query, "sources": []}
    
    req.query = validated_query

    # 3. Conversation Handling (DB logic)
    db = SessionLocal()
    try:
        conv_repo = ConversationRepository(db)
        if not req.conversation_id:
            conv = conv_repo.create_conversation(user_id)
            conversation_id = str(conv.id)
        else:
            conversation_id = req.conversation_id
    finally:
        db.close() # Close immediately after getting the ID

    req.session_id = conversation_id

    try:
        # 4. PRE-CHECK: Cache
        cache_key = get_llm_cache_key(req)
        cached = get_cache(cache_key)
        if cached:
            logger.info(f"cache_hit=true key={cache_key}")
            return JSONResponse(
                content=cached,
                headers={"X-Conversation-Id": conversation_id}
            )

        # 5. Core Chat Logic
        response = chat_service.handle_chat(req)
        
        # Add metadata to response
        response["conversation_id"] = conversation_id
        response["latency"] = round(time.time() - start_time, 3)

        # 6. Post-Processing: Background Task
        # We save history and cache in the background to return the response faster
        answer = response.get("answer")
        if answer and "Not found in context" not in answer:
            background_tasks.add_task(
                finalize_chat_session,
                req=req,
                full_answer=answer,
                cache_key=cache_key
            )

        # 7. Return with Header
        return JSONResponse(
            content=response,
            headers={"X-Conversation-Id": conversation_id}
        )

    except Exception as e:
        logger.error(f"chat_route_failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"query": req.query, "answer": "Internal server error.", "sources": []}
        )
      
        
@router.post("/chat/stream")
def stream_chat(req: ChatRequest, request: Request, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    client_ip = request.client.host

    # PRE-CHECK 1: Rate Limiting (Returns JSON, no SSE opened)
    if not rate_limiter.allow(f"rate:{client_ip}"):
        return {
            "query": req.query,
            "answer": "Too many requests. Please try again later.",
            "sources": []
        }

    # PRE-CHECK 2: Validation (Returns JSON, no SSE opened)
    is_valid, validated_query = validator.validate(req.query)
    if not is_valid:
        return {
            "query": req.query, 
            "answer": validated_query, 
            "sources": []
        }

    req.query = validated_query
    
    # Conversation Handling (DB logic)
    # We use 'with' or try/finally to ensure db.close() always runs
    db = SessionLocal()
    try:
        conv_repo = ConversationRepository(db)
        if not req.conversation_id:
            conv = conv_repo.create_conversation(user_id)
            conversation_id = str(conv.id)
        else:
            conversation_id = req.conversation_id
    finally:
        db.close()
        
    # Crucial: Use conversation_id as the session_id for memory retrieval
    req.session_id = conversation_id
        
    # PRE-CHECK 3: Cache (Returns JSON, no SSE opened)
    cache_key = get_llm_cache_key(req)
    cached = get_cache(cache_key)
    if cached:
        logger.info(f"cache_hit=true key={cache_key}")
         # FIX: Wrap the dict in JSONResponse to attach the header
        return JSONResponse(
            content=cached,
            headers={"X-Conversation-Id": conversation_id}
        )

    def event_generator():
        full_answer = ""
        try:
            # Core Logic Execution via Service
            for chunk in chat_service.stream_chat(req):
                if chunk:
                    full_answer += chunk
                    yield f"data: {chunk}\n\n"
            
            # Save Cache after stream completion
            if full_answer and "Not found in context" not in full_answer:
                background_tasks.add_task(
                    finalize_chat_session,
                    req=req,
                    full_answer=full_answer,
                    cache_key=cache_key
                )
                
        except Exception as e:
            logger.error(f"stream_failed: {e}")
            yield f"data: {json.dumps({'error': 'Stream interrupted'})}\n\n"


    # 5. Build Response and add Custom Header
    response = StreamingResponse(event_generator(), media_type="text/event-stream")
    response.headers["X-Conversation-Id"] = conversation_id
    
    return response
