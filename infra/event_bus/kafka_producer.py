import json
from aiokafka import AIOKafkaProducer
from infra.event_bus.kafka_config import KAFKA_BOOTSTRAP
from shared.logging import get_logger

logger = get_logger(__name__)


class KafkaProducerService:

    def __init__(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode(),
            linger_ms=20,
            acks="all",
            retries=5
        )

    async def start(self):
        await self.producer.start()

    async def stop(self):
        await self.producer.stop()

    async def send(self, topic: str, data: dict):
        try:
            await self.producer.send_and_wait(topic, payload)
        except Exception as e:
            logger.error(f"kafka_send_failed: {e}")