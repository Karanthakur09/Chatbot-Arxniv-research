from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
import time
from sqlalchemy.ext.asyncio import AsyncSession
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
from services.api_gateway.middleware.rate_limiter import limiter
from fastapi.responses import StreamingResponse
import json
import hashlib
from fastapi.responses import JSONResponse
from infra.db.session import AsyncSessionLocal # 2. Use AsyncSessionLocal
from services.api_gateway.dependencies.db import get_db
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
async def finalize_chat_session(req: ChatRequest, full_answer: str, cache_key: str):
    """Async background task to save cache and memory"""
    try:
        await set_cache(cache_key, {"query": req.query, "answer": full_answer}, ttl=60)
        await chat_service.memory.save(req.session_id, req.query, full_answer)
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


# ---------------------------
# Route
# ---------------------------

@router.post("/chat")
# SlowAPI automatically uses the 'request' object to track the user
@limiter.limit("20/minute") 
async def chat( # Add async
    req: ChatRequest, 
    request: Request, 
    background_tasks: BackgroundTasks, 
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db) # 5. Use the async DB dependency
):
    start_time = time.time()

    # 2. PRE-CHECK: Validation
    is_valid, validated_query = validator.validate(req.query)
    if not is_valid:
        return {"query": req.query, "answer": validated_query, "sources": []}
    
    req.query = validated_query

    # 3. Conversation Handling (DB logic)
    try:
        conv_repo = ConversationRepository(db)
        if not req.conversation_id:
            conv = await conv_repo.create_conversation(user_id)
            conversation_id = str(conv.id)
        else:
            conversation_id = req.conversation_id
    except Exception as e:
        logger.error(f"db_error: {e}")
        conversation_id = req.conversation_id or "temp_session"

    req.session_id = conversation_id

    try:
        # 4. PRE-CHECK: Cache
        cache_key = get_llm_cache_key(req)
        cached = await get_cache(cache_key)
        if cached:
            logger.info(f"cache_hit=true key={cache_key}")
            return JSONResponse(
                content=cached,
                headers={"X-Conversation-Id": conversation_id}
            )

        # 5. Core Chat Logic
        response = await chat_service.handle_chat(req) # Must await!
        
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
@limiter.limit("20/minute") 
async def stream_chat( # Add async
    req: ChatRequest, 
    request: Request, 
    background_tasks: BackgroundTasks, 
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db) # 10. Inject db
):   


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
    try:
        conv_repo = ConversationRepository(db)
        if not req.conversation_id:
            conv = await conv_repo.create_conversation(user_id)
            conversation_id = str(conv.id)
        else:
            conversation_id = req.conversation_id
    except Exception as e:
        logger.error(f"db_error: {e}")
        conversation_id = req.conversation_id or "temp_session"
        
    # Crucial: Use conversation_id as the session_id for memory retrieval
    req.session_id = conversation_id
        
    # PRE-CHECK 3: Cache (Returns JSON, no SSE opened)
    cache_key = get_llm_cache_key(req)
    cached = await get_cache(cache_key)
    if cached:
        logger.info(f"cache_hit=true key={cache_key}")
        return JSONResponse(
            content=cached,
            headers={"X-Conversation-Id": conversation_id}
        )

    async def event_generator(): # Must be 'async def'
        full_answer = ""
        try:
            # chat_service.stream_chat MUST now be an async generator
            async for chunk in chat_service.stream_chat(req): 
                if chunk:
                    full_answer += chunk
                    yield f"data: {chunk}\n\n"
            
            if full_answer and "Not found in context" not in full_answer:
                background_tasks.add_task(finalize_chat_session, req, full_answer, cache_key)
                
        except Exception as e:
            logger.error(f"stream_error: {e}")
            yield "data: [ERROR]\n\n"

    # 5. Build Response and add Custom Header
    response = StreamingResponse(event_generator(), media_type="text/event-stream")
    response.headers["X-Conversation-Id"] = conversation_id
    
    return response
