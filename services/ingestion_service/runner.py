from shared.queue import blocking_pop, INGESTION_QUEUE
from services.ingestion_service.tasks import process_document
from shared.logging import get_logger

logger = get_logger(__name__)

def start_ingestion():
    logger.info("Reader consumer started")
    while True:
        job = blocking_pop(INGESTION_QUEUE)
        if job:
            process_document.delay(job)
            
if __name__ == "__main__":
    start_ingestion()