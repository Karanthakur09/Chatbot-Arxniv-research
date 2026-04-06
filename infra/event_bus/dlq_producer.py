from shared.logging import get_logger

logger = get_logger(__name__)

class DLQProducer:

    def __init__(self, producer):
        self.producer = producer

    async def send(self, topic: str, data: dict):
        try:
            await self.producer.send(topic, data)
        except Exception as e:
            logger.error(f"DLQ_send_failed: {e}")
                