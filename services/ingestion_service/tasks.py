from services.ingestion_service.worker import celery_app
from services.ingestion_service.r2_reader import R2Reader
from services.ingestion_service.parser import extract_text_from_pdf
from services.ingestion_service.cleaner import clean_text
from services.ingestion_service.table_extractor import extract_tables_from_pdf
from shared.queue import push, EMBEDDING_QUEUE, OCR_QUEUE
from shared.logging import get_logger

logger = get_logger(__name__)

r2 = R2Reader()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def process_document(self, payload: dict):

    doc_id = payload["doc_id"]
    key = payload["r2_key"]

    logger.info(f"[INGEST START] {doc_id}")

    try:
        # Step 1: Fetch PDF
        pdf_bytes = r2.get_pdf(key)

        # Step 2: Extract text
        text = extract_text_from_pdf(pdf_bytes)
        
        # Step 3:update pipline with table extraction
        tables = extract_tables_from_pdf(pdf_bytes)
        
        # Step 4: OCR detection (simple)
        needs_ocr = len(text.strip()) < 500

        if not text:
            raise ValueError("Empty extracted text")

        # Step 5: Clean text
        text = clean_text(text)

        # Step 6: Push to embedding queue
        if needs_ocr:
            push(OCR_QUEUE, {
                "doc_id": doc_id,
                "text": text,
                "tables": tables,
                "needs_ocr": needs_ocr,
                "status": "extracted"
            })
        else:
            push(EMBEDDING_QUEUE, {
                "doc_id": doc_id,
                "text": text,
                "tables": tables,
                "needs_ocr": needs_ocr,
                "status": "extracted"
            })

        logger.info(f"[INGEST SUCCESS] {doc_id}")

    except Exception as e:
        logger.error(f"[INGEST FAILED] {doc_id} | {e}")
        raise e