from services.downloader_service.celery_app import celery_app
from services.downloader_service.downloader import download_pdf_stream
from services.downloader_service.validator import is_valid_pdf
from services.downloader_service.r2_client import R2Client

from shared.queue import push, INGESTION_QUEUE
from shared.logging import get_logger

logger = get_logger(__name__)

r2 = R2Client()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def process_pdf(self, payload: dict):

    doc_id = payload["doc_id"]
    url = payload["download_url"]
    retry_count = payload.get("retry_count", 0)

    logger.info(f"[START] {doc_id} | retry={retry_count}")

    try:
        # Step 1: Download
        pdf_data = download_pdf_stream(url)

        # Step 2: Validate
        if not is_valid_pdf(pdf_data):
            raise ValueError("Invalid PDF format")

        # Step 3: Upload to R2
        key = f"raw_pdfs/{doc_id}.pdf"

        success = r2.upload_pdf(key, pdf_data)

        if not success:
            raise RuntimeError("Upload failed")

        # Step 4: Push to ingestion queue
        push(INGESTION_QUEUE, {
            "doc_id": doc_id,
            "r2_key": key,
            "status": "downloaded"
        })

        logger.info(f"[SUCCESS] {doc_id}")

    except Exception as e:
        logger.error(f"[FAILED] {doc_id} | {e}")
        raise e  # triggers retry