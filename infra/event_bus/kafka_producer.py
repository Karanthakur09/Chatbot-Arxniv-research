import json
from aiokafka import AIOKafkaProducer
from infra.event_bus.kafka_config import KAFKA_BOOTSTRAP
from shared.logging import get_logger

logger = get_logger(__name__)


class KafkaProducerService:

    def __init__(self):
        self.producer = None

    async def _init_producer(self):
        """Initialize Kafka producer in async context"""
        if self.producer is None:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode(),
                linger_ms=20,
                acks="all"
            )

    async def start(self):
        await self._init_producer()
        await self.producer.start()

    async def stop(self):
        await self.producer.stop()

    async def send(self, topic: str, data: dict):
        
        try:
            await self.producer.send_and_wait(topic, data)
        except Exception as e:
            logger.error(f"kafka_send_failed: {e}")