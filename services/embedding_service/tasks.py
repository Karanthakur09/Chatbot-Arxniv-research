from services.embedding_service.worker import celery_app

from services.embedding_service.chunker.text_chunker import chunk_text
from services.embedding_service.chunker.table_chunker import table_to_chunks
from services.embedding_service.embedder import generate_embeddings
from services.embedding_service.store import store_embeddings

from shared.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def process_embedding(self, payload: dict):

    doc_id = payload["doc_id"]
    text = payload.get("text", "")
    tables = payload.get("tables", [])
    needs_ocr = payload.get("needs_ocr", False)

    source = "ocr" if needs_ocr else "text"

    logger.info(f"[EMBED START] {doc_id} | source={source}")

    try:
        # Step 1: Chunk text
        text_chunks = chunk_text(text)

        # Step 2: Chunk tables
        table_chunks = table_to_chunks(tables)

        # Merge
        all_chunks = text_chunks + table_chunks

        if not all_chunks:
            raise ValueError("No chunks generated")

        contents = [c["content"] for c in all_chunks]

        # Step 3: Embeddings
        embeddings = generate_embeddings(contents)

        # Step 4: Store
        store_embeddings(doc_id, all_chunks, embeddings, source)

        logger.info(f"[EMBED SUCCESS] {doc_id} | chunks={len(all_chunks)}")

    except Exception as e:
        logger.error(f"[EMBED FAILED] {doc_id} | {e}")
        raise e