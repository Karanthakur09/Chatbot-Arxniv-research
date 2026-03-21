from shared.queue import blocking_pop, OCR_QUEUE
from services.ocr_service.tasks import process_ocr
from shared.logging import get_logger

logger = get_logger(__name__)

def start_ocr():
    while True:
        logger.info("OCR reader started")
        job = blocking_pop(OCR_QUEUE)
        if job:
            process_ocr.delay(job)
            
if __name__ == "__main__":
    start_ocr()