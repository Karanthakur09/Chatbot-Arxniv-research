from fastapi import APIRouter, Request, Depends, BackgroundTasks
from pydantic import BaseModel
import time
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse, StreamingResponse

# Core Logic & Dependencies
from core.chat.chat_service import ChatService
from core.chat.validator import QueryValidator
from services.api_gateway.dependencies.chat import get_chat_service
from services.api_gateway.dependencies.auth import get_current_user
from services.api_gateway.dependencies.db import get_db

# Infrastructure & Shared
from shared.logging import get_logger
from shared.cache import get_cache, set_cache
from services.api_gateway.middleware.rate_limiter import limiter
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
    """Generates a consistent, hashed cache key."""
    clean_query = req.query.strip().lower()
    source = req.source or "all"
    chunk_type = req.chunk_type or "standard"
    raw_key = f"{req.session_id}:{clean_query}:{source}:{chunk_type}"
    return f"llm_cache:{hashlib.md5(raw_key.encode()).hexdigest()}"


# Updated Background Worker: Now accepts chat_service to save memory
async def finalize_chat_session(req: ChatRequest, full_answer: str, cache_key: str, chat_service: ChatService):
    """Async background task to save cache and memory"""
    try:
        await set_cache(cache_key, {"query": req.query, "answer": full_answer}, ttl=60)
        # Use the service passed from the route
        await chat_service.memory.save(req.session_id, req.query, full_answer)
        logger.info(f"background_save_complete session={req.session_id}")
    except Exception as e:
        logger.error(f"background_save_failed: {e}")


# Global Validator
validator = QueryValidator()


# ---------------------------
# Route: Standard Chat
# ---------------------------

@router.post("/chat")
@limiter.limit("20/minute") 
async def chat(
    req: ChatRequest, 
    request: Request, 
    background_tasks: BackgroundTasks, 
    user_id: str = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service), 
    db: AsyncSession = Depends(get_db)
):
    start_time = time.time()

    # 1. Validation
    is_valid, validated_query = validator.validate(req.query)
    if not is_valid:
        return {"query": req.query, "answer": validated_query, "sources": []}
    
    req.query = validated_query

    # 2. Conversation Handling
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
        # 3. Cache Check
        cache_key = get_llm_cache_key(req)
        cached = await get_cache(cache_key)
        if cached:
            logger.info(f"cache_hit=true key={cache_key}")
            return JSONResponse(
                content=cached,
                headers={"X-Conversation-Id": conversation_id}
            )

        # 4. Core Chat Logic (Kafka event is fired inside here)
        response = await chat_service.handle_chat(req)
        
        response["conversation_id"] = conversation_id
        response["latency"] = round(time.time() - start_time, 3)

        # 5. Background Tasks
        answer = response.get("answer")
        if answer and "Not found in context" not in answer:
            background_tasks.add_task(
                finalize_chat_session,
                req=req,
                full_answer=answer,
                cache_key=cache_key,
                chat_service=chat_service # Passed correctly
            )
            
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
        
        
# ---------------------------
# Route: Stream Chat
# ---------------------------

@router.post("/chat/stream")
@limiter.limit("20/minute") 
async def stream_chat(
    req: ChatRequest, 
    request: Request, 
    background_tasks: BackgroundTasks, 
    user_id: str = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    db: AsyncSession = Depends(get_db)
):   
    # 1. Validation
    is_valid, validated_query = validator.validate(req.query)
    if not is_valid:
        return {"query": req.query, "answer": validated_query, "sources": []}

    req.query = validated_query
    
    # 2. Conversation Handling
    try:
        conv_repo = ConversationRepository(db)
        conversation_id = req.conversation_id
        if not conversation_id:
            conv = await conv_repo.create_conversation(user_id)
            conversation_id = str(conv.id)
    except Exception as e:
        logger.error(f"db_error: {e}")
        conversation_id = req.conversation_id or "temp_session"
        
    req.session_id = conversation_id
        
    # 3. Cache Check
    cache_key = get_llm_cache_key(req)
    cached = await get_cache(cache_key)
    if cached:
        return JSONResponse(content=cached, headers={"X-Conversation-Id": conversation_id})

    async def event_generator():
        full_answer = ""
        try:
            # Kafka event is fired inside stream_chat once generation ends
            async for chunk in chat_service.stream_chat(req): 
                if chunk:
                    full_answer += chunk
                    yield f"data: {chunk}\n\n"
            
            if full_answer and "Not found in context" not in full_answer:
                background_tasks.add_task(
                    finalize_chat_session, 
                    req, 
                    full_answer, 
                    cache_key, 
                    chat_service
                )
        except Exception as e:
            logger.error(f"stream_error: {e}")
            yield "data: [ERROR]\n\n"

    response = StreamingResponse(event_generator(), media_type="text/event-stream")
    response.headers["X-Conversation-Id"] = conversation_id
    return response
