from services.ocr_service.worker import celery_app
from services.ocr_service.ocr_engine import extract_text_via_ocr
from services.ingestion_service.r2_reader import R2Reader

from shared.queue import push, EMBEDDING_QUEUE
from shared.logging import get_logger

logger = get_logger(__name__)

r2 = R2Reader()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def process_ocr(self, payload: dict):

    doc_id = payload["doc_id"]
    key = payload["r2_key"]

    logger.info(f"[OCR START] {doc_id}")

    try:
        # Step 1: Fetch PDF
        pdf_bytes = r2.get_pdf(key)

        # Step 2: OCR
        text = extract_text_via_ocr(pdf_bytes)

        if not text:
            raise ValueError("OCR returned empty text")

        # Step 3: Push back to embedding
        push(EMBEDDING_QUEUE, {
            "doc_id": doc_id,
            "text": text,
            "tables": payload.get("tables", []),
            "needs_ocr": False,
            "status": "ocr_done"
        })

        logger.info(f"[OCR SUCCESS] {doc_id}")

    except Exception as e:
        logger.error(f"[OCR FAILED] {doc_id} | {e}")
        raise e