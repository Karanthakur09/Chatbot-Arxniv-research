
import redis.asyncio as redis
import json
from shared.config import settings
from shared.redis_client import get_redis_client

PDF_DOWNLOAD_QUEUE = "pdf_download_queue"
INGESTION_QUEUE = "ingestion_queue"
EMBEDDING_QUEUE = "embedding_queue"
OCR_QUEUE = "ocr_queue"

async def push(queue_name, payload):
    """Async push to queue"""
    redis_client = await get_redis_client()
    await redis_client.lpush(queue_name, json.dumps(payload))


async def blocking_pop(queue_name, timeout=0):
    """Async blocking pop from queue"""
    redis_client = await get_redis_client()
    item = await redis_client.brpop(queue_name, timeout=timeout or None)
    if item:
        return json.loads(item[1])
    return None