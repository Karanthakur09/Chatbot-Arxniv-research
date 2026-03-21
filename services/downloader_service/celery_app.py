from celery import Celery
from shared.config import settings
from dotenv import load_dotenv

load_dotenv()

celery_app = Celery(
    "downloader_service",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,  # ensures task is not lost
    worker_prefetch_multiplier=1  # prevents worker overload
)