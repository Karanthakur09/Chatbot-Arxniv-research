from shared.queue import blocking_pop, EMBEDDING_QUEUE
from services.embedding_service.tasks import process_embedding
from shared.logging import get_logger

logger = get_logger(__name__)


def start_embedding():

    logger.info("Embedding runner started")

    while True:
        job = blocking_pop(EMBEDDING_QUEUE)

        if job:
            logger.info(f"Job received: {job.get('doc_id')}")
            process_embedding.delay(job)


if __name__ == "__main__":
    start_embedding()