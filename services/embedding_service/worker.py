from celery import Celery
from shared.config import settings

celery_app = Celery(
    "ingestion_service",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"
)

# ADD THIS
celery_app.autodiscover_tasks([
    "services.embedding_service"
])