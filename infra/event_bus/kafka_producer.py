import json
import asyncio
from aiokafka import AIOKafkaProducer
from infra.event_bus.kafka_config import KAFKA_BOOTSTRAP
from shared.logging import get_logger

logger = get_logger(__name__)


class KafkaProducerService:

    def __init__(self):
        self.producer = None
        self.connected = False
        self.max_retries = 5
        self.initial_backoff = 2

    async def _init_producer(self):
        """Initialize Kafka producer in async context"""
        if self.producer is None:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode(),
                linger_ms=20,
                acks="all"
            )

    async def start(self, blocking=False):
        """Start Kafka producer with retry logic.
        
        Args:
            blocking: If True, retry until connected. If False, return after max retries.
        """
        await self._init_producer()
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP} (attempt {attempt}/{self.max_retries})")
                await self.producer.start()
                self.connected = True
                logger.info("Successfully connected to Kafka")
                return
            except Exception as e:
                logger.error(f"Kafka connection failed (attempt {attempt}): {type(e).__name__}: {str(e)}")
                self.connected = False
                
                if attempt == self.max_retries:
                    if blocking:
                        logger.critical(f"Failed to connect to Kafka after {self.max_retries} attempts. Cannot continue.")
                        raise
                    else:
                        logger.warning(f"Failed to connect to Kafka after {self.max_retries} attempts. API will continue without Kafka.")
                        return
                
                backoff = self.initial_backoff ** (attempt - 1)
                logger.info(f"Retrying Kafka connection in {backoff} seconds...")
                await asyncio.sleep(backoff)

    async def stop(self):
        if self.producer:
            try:
                await self.producer.stop()
            except Exception as e:
                logger.error(f"Error stopping Kafka producer: {e}")

    async def send(self, topic: str, data: dict):
        "Send message to Kafka topic. Returns True if successful, False otherwise."
        if not self.connected or not self.producer:
            logger.warning(f"Kafka not connected. Message to '{topic}' was not sent")
            return False
        
        try:
            await self.producer.send_and_wait(topic, data)
            return True
        except Exception as e:
            logger.error(f"kafka_send_failed on topic '{topic}': {type(e).__name__}: {e}")
            return False