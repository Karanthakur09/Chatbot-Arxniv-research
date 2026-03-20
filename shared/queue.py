# import redis
# import json
# from shared.config import settings

# redis_client = redis.Redis(
#     host=settings.REDIS_HOST,
#     port=settings.REDIS_PORT,
#     decode_responses=True
# )

# QUEUE_NAME = "document_ingestion_queue"


# def push_document(payload):

#     redis_client.lpush(
#         QUEUE_NAME,
#         json.dumps(payload)
#     )


# def pop_document():
#     # doesn't lead to busy polling, workers wait until job arrives
#     item = redis_client.brpop(QUEUE_NAME)

#     if item:
#         return json.loads(item)

#     return None


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


def push(queue_name, payload):
    redis_client.lpush(queue_name, json.dumps(payload))


def blocking_pop(queue_name):
    item = redis_client.brpop(queue_name)
    if item:
        return json.loads(item[1])
    return None