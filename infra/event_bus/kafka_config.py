from shared.config import settings

KAFKA_BOOTSTRAP = settings.KAFKA_BOOTSTRAP
TOPICS = {
    "chat_events": "chat_events",
    "dlq": "chat_events_dlq"
}