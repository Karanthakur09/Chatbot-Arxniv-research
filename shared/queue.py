
import redis
import json
from shared.config import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True
)

PDF_DOWNLOAD_QUEUE = "pdf_download_queue"
INGESTION_QUEUE = "ingestion_queue"
EMBEDDING_QUEUE = "embedding_queue"
OCR_QUEUE = "ocr_queue"

def push(queue_name, payload):
    redis_client.lpush(queue_name, json.dumps(payload))


def blocking_pop(queue_name):
    item = redis_client.brpop(queue_name)
    if item:
        return json.loads(item[1])
    return None