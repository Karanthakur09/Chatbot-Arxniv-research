from fastapi import FastAPI
from shared.logging import get_logger
from services.api_gateway.routes.chat import router as chat_router
from services.api_gateway.routes.auth import router as auth_router
from services.api_gateway.routes.conversations import router as conv_router
from services.api_gateway.producer import kafka_producer

logger = get_logger(__name__)
app = FastAPI(title="Enterprise Chatbot")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    """Start Kafka producer with non-blocking retry logic."""
    try:
        # Non-blocking: don't crash if Kafka is unavailable
        await kafka_producer.start(blocking=False)
    except Exception as e:
        logger.error(f"Kafka startup error (non-fatal): {e}")
        # Continue running without Kafka - messages will fail gracefully

@app.on_event("shutdown")
async def shutdown():
    try:
        await kafka_producer.stop()
    except Exception as e:
        logger.error(f"Kafka shutdown error: {e}")


# app.include_router(search_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(conv_router)