import json
import asyncio
from aiokafka import AIOKafkaConsumer

from infra.event_bus.kafka_config import KAFKA_BOOTSTRAP, TOPICS
from infra.data_warehouse.snowflake_async import SnowflakeAsyncService
from shared.logging import get_logger

logger = get_logger(__name__)


class SnowflakeConsumer:

    def __init__(self):
        self.consumer = AIOKafkaConsumer(
            TOPICS["chat_events"],
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id="snowflake-group",
            enable_auto_commit=False
        )

        self.dlq_producer = None  # reuse producer later
        self.snowflake = SnowflakeAsyncService()
        self.batch = []
        self.batch_size = 50

    async def start(self):
        await self.consumer.start()

        try:
            async for msg in self.consumer:
                self.batch.append(msg.value)

                if len(self.batch) >= self.batch_size:
                    await self._flush()

        finally:
            await self.consumer.stop()

    async def _flush(self):
        try:
            await self.snowflake.insert_batch(self.batch)
            await self.consumer.commit()
            self.batch.clear()

        except Exception as e:
            logger.error(f"snowflake_batch_failed: {e}")

            # DLQ handling
            for event in self.batch:
                logger.error(f"DLQ event: {event}")

            self.batch.clear()