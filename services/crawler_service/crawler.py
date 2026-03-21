import os
import json
import time

from services.crawler_service.arxiv_client import ArxivClient
from shared.config import settings
from shared.logging import get_logger
from shared.queue import push, PDF_DOWNLOAD_QUEUE

logger = get_logger(__name__)

client = ArxivClient(query="all:ai", batch_size=100)

METADATA_DIR = os.path.join(settings.DATA_DIR, "metadata")
STATE_FILE = os.path.join(settings.DATA_DIR, "last_seen_id.txt")

os.makedirs(METADATA_DIR, exist_ok=True)


# Read last seen ID
def get_last_seen_id():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r") as f:
        return f.read().strip()


# Save latest ID
def save_last_seen_id(doc_id):
    with open(STATE_FILE, "w") as f:
        f.write(str(doc_id))


def crawl_documents(limit=5000):

    start = 0
    collected = 0

    logger.info("Arxiv crawler started")

    last_seen_id = get_last_seen_id()
    logger.info(f"Last seen ID: {last_seen_id}")

    first_run_highest_id = None
    stop = False

    while collected < limit:

        entries = client.fetch_batch(start=start)

        if not entries:
            logger.info("No results returned")
            break

        for doc in entries:

            doc_id = doc["doc_id"]
            download_url = doc["download_url"]

            if not doc_id:
                continue

            # STOP if already processed
            if last_seen_id and doc_id == last_seen_id:
                logger.info("Reached already processed data. Stopping...")
                stop = True
                break

            # Track latest ID
            if collected == 0:
                first_run_highest_id = doc_id

            file_path = os.path.join(METADATA_DIR, f"{doc_id}.json")

            # Skip if already exists
            if os.path.exists(file_path):
                continue

            # Save metadata
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2)

            # Push to queue
            if download_url:
                payload = {
                    "doc_id": doc_id,
                    "download_url": download_url,
                    "title": doc.get("title"),
                    "category": doc.get("category"),
                    "published": doc.get("published"),
                    "status": "pending"
                }

                push(PDF_DOWNLOAD_QUEUE, payload)

            else:
                logger.warning(f"No PDF for doc {doc_id}")

            collected += 1

            if collected % 100 == 0:
                logger.info(f"{collected} documents processed & queued")

            if collected >= limit:
                break

        if stop:
            break

        # Move pagination
        start += client.batch_size

    # Save latest ID
    if first_run_highest_id:
        save_last_seen_id(first_run_highest_id)

    logger.info(f"Crawler finished: {collected} new documents")


if __name__ == "__main__":
    crawl_documents(5000)