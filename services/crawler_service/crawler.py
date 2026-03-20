# # import os
# # import json

# # from services.crawler_service.courtlistener_client import CourtListenerClient
# # from shared.config import settings
# # from shared.logging import get_logger

# # logger = get_logger(__name__)

# # client = CourtListenerClient()

# # METADATA_DIR = os.path.join(settings.DATA_DIR, "metadata")

# # os.makedirs(METADATA_DIR, exist_ok=True)


# # def crawl_opinions(limit=5000):

# #     next_page = None
# #     collected = 0

# #     logger.info("Crawler started")

# #     while collected < limit:

# #         data = client.fetch_page(next_page)

# #         results = data["results"]
        
# #         from shared.queue import push, PDF_DOWNLOAD_QUEUE

# #         for opinion in results:

# #             opinion_id = opinion.get("id")
# #             download_url = opinion.get("download_url")

# #             # Save metadata
# #             file_path = os.path.join(
# #                 METADATA_DIR,
# #                 f"{opinion_id}.json"
# #             )

# #             with open(file_path, "w", encoding="utf-8") as f:
# #                 json.dump(opinion, f, indent=2)

# #             # Push to queue if PDF exists
# #             if download_url:

# #                 payload = {
# #                     "opinion_id": opinion_id,
# #                     "download_url": download_url,
# #                     "case_name": opinion.get("case_name"),
# #                     "court": opinion.get("court"),
# #                     "date_filed": opinion.get("date_filed"),
# #                     "status": "pending"
# #                 }

# #                 push(PDF_DOWNLOAD_QUEUE, payload)

# #             collected += 1

# #             # Keep logging
# #             if collected % 100 == 0:
# #                 logger.info(f"{collected} opinions processed & queued")

# #             if collected >= limit:
# #                 break
        
# #         next_page = data["next"]

# #         if not next_page:
# #             logger.info("No more pages available")
# #             break

# #     logger.info(f"Crawler finished: {collected} opinions")
# import os
# import json
# import time

# from services.crawler_service.courtlistener_client import CourtListenerClient
# from shared.config import settings
# from shared.logging import get_logger
# from shared.queue import push, PDF_DOWNLOAD_QUEUE

# logger = get_logger(__name__)

# client = CourtListenerClient()

# METADATA_DIR = os.path.join(settings.DATA_DIR, "metadata")
# os.makedirs(METADATA_DIR, exist_ok=True)


# def crawl_opinions(limit=5000):

#     next_page = None
#     collected = 0

#     logger.info("Crawler started")

#     while collected < limit:

#         data = client.fetch_page(next_page)

#         results = data.get("results", [])

#         for opinion in results:

#             opinion_id = opinion.get("id")
#             download_url = opinion.get("download_url")

#             if not opinion_id:
#                 continue

#             # Save metadata
#             file_path = os.path.join(
#                 METADATA_DIR,
#                 f"{opinion_id}.json"
#             )

#             with open(file_path, "w", encoding="utf-8") as f:
#                 json.dump(opinion, f, indent=2)

#             # Extract court safely
#             court = opinion.get("court", {})

#             # Push only if PDF exists
#             if download_url:

#                 payload = {
#                     "opinion_id": opinion_id,
#                     "download_url": download_url,
#                     "case_name": opinion.get("case_name"),
#                     "court": court.get("name"),
#                     "date_filed": opinion.get("date_filed"),
#                     "status": "pending"
#                 }

#                 push(PDF_DOWNLOAD_QUEUE, payload)

#             else:
#                 logger.warning(f"No PDF for opinion {opinion_id}")

#             collected += 1

#             if collected % 100 == 0:
#                 logger.info(f"{collected} opinions processed & queued")

#             if collected >= limit:
#                 break

#         next_page = data.get("next")

#         if not next_page:
#             logger.info("No more pages available")
#             break

#         # IMPORTANT: prevent API blocking
#         time.sleep(1)

#     logger.info(f"Crawler finished: {collected} opinions")
    
    
# if __name__ == "__main__":
#     crawl_opinions(5000)



import os
import json
import time

from services.crawler_service.courtlistener_client import CourtListenerClient
from shared.config import settings
from shared.logging import get_logger
from shared.queue import push, PDF_DOWNLOAD_QUEUE

logger = get_logger(__name__)

client = CourtListenerClient()

METADATA_DIR = os.path.join(settings.DATA_DIR, "metadata")
STATE_FILE = os.path.join(settings.DATA_DIR, "last_seen_id.txt")

os.makedirs(METADATA_DIR, exist_ok=True)


# ✅ Read last seen ID
def get_last_seen_id():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r") as f:
        return f.read().strip()


# ✅ Save latest ID
def save_last_seen_id(opinion_id):
    with open(STATE_FILE, "w") as f:
        f.write(str(opinion_id))


def crawl_opinions(limit=5000):

    next_page = None
    collected = 0

    logger.info("Crawler started")

    last_seen_id = get_last_seen_id()
    logger.info(f"Last seen ID: {last_seen_id}")

    first_run_highest_id = None
    stop = False

    while collected < limit:

        data = client.fetch_page(next_page)

        results = data.get("results", [])
        next_page = data.get("next")

        if not results:
            logger.info("No results returned")
            break

        for opinion in results:

            opinion_id = opinion.get("id")
            download_url = opinion.get("download_url")

            if not opinion_id:
                continue

            opinion_id = str(opinion_id)

            # 🛑 STOP when old data reached
            if last_seen_id and opinion_id == last_seen_id:
                logger.info("Reached already processed data. Stopping...")
                stop = True
                break

            # ✅ Track latest ID (first item of first page)
            if collected == 0:
                first_run_highest_id = opinion_id

            file_path = os.path.join(METADATA_DIR, f"{opinion_id}.json")

            # ✅ Skip if already exists (extra safety)
            if os.path.exists(file_path):
                continue

            # ✅ Save metadata
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(opinion, f, indent=2)

            # Extract court safely
            court = opinion.get("court", {})

            # ✅ Push only if PDF exists
            if download_url:
                payload = {
                    "opinion_id": opinion_id,
                    "download_url": download_url,
                    "case_name": opinion.get("case_name"),
                    "court": court.get("name"),
                    "date_filed": opinion.get("date_filed"),
                    "status": "pending"
                }

                push(PDF_DOWNLOAD_QUEUE, payload)

            else:
                logger.warning(f"No PDF for opinion {opinion_id}")

            collected += 1

            if collected % 100 == 0:
                logger.info(f"{collected} opinions processed & queued")

            if collected >= limit:
                break

        if stop:
            break

        if not next_page:
            logger.info("No more pages available")
            break

        # ✅ IMPORTANT: avoid blocking
        time.sleep(3)

    # ✅ Save latest ID for next run
    if first_run_highest_id:
        save_last_seen_id(first_run_highest_id)

    logger.info(f"Crawler finished: {collected} new opinions")


if __name__ == "__main__":
    crawl_opinions(5000)