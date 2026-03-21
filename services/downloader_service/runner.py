from shared.queue import blocking_pop, PDF_DOWNLOAD_QUEUE
from services.downloader_service.tasks import process_pdf
from shared.logging import get_logger

logger = get_logger(__name__)

def start_consumer():

    logger.info("Downloader consumer started")

    while True:
        job = blocking_pop(PDF_DOWNLOAD_QUEUE)
        
        logger.info(f"Received job: {job}")
        if job:
            process_pdf.delay(job)
            
if __name__ == "__main__":
    start_consumer()