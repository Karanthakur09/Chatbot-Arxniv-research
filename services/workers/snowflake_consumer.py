import json
import asyncio
from datetime import datetime

from aiokafka import AIOKafkaConsumer

from infra.data_warehouse.snowflake_async import SnowflakeAsyncService
from infra.event_bus.kafka_config import TOPICS, KAFKA_BOOTSTRAP
from infra.event_bus.kafka_producer import KafkaProducerService

from shared.logging import get_logger

logger = get_logger(__name__)


class SnowflakeConsumer:

    def __init__(self):
        self.consumer = None
        self.snowflake = None
        self.batch = []
        self.batch_size = 20
        self.dlq_producer = KafkaProducerService()  # DLQ

    async def _init_consumer(self):
        """Initialize Kafka consumer in async context with retry logic"""
        if self.consumer is None:
            max_retries = 5
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    self.consumer = AIOKafkaConsumer(
                        TOPICS["chat_events"],
                        bootstrap_servers=KAFKA_BOOTSTRAP,
                        group_id="snowflake-group",
                        enable_auto_commit=False,
                        auto_offset_reset='earliest',
                        session_timeout_ms=10000,
                        request_timeout_ms=40000
                    )
                    logger.info("Kafka consumer initialized successfully")
                    return
                    
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Failed to initialize consumer (attempt {retry_count}/{max_retries}): {e}")
                    if retry_count < max_retries:
                        await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    else:
                        logger.error("Failed to initialize consumer after max retries")
                        raise

    async def _init_snowflake(self):
        """Initialize Snowflake service in async context"""
        if self.snowflake is None:
            self.snowflake = SnowflakeAsyncService()

    async def start(self):
        await self._init_consumer()
        await self._init_snowflake()
        
        # Retry starting consumer with exponential backoff
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                await self.consumer.start()
                logger.info("Consumer started successfully")
                break
            except Exception as e:
                retry_count += 1
                logger.warning(f"Failed to start consumer (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(2 ** retry_count)
                else:
                    logger.error("Failed to start consumer after max retries")
                    raise
        
        # Start DLQ producer
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                await self.dlq_producer.start()
                logger.info("DLQ producer started successfully")
                break
            except Exception as e:
                retry_count += 1
                logger.warning(f"Failed to start DLQ producer (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(2 ** retry_count)
                else:
                    logger.error("Failed to start DLQ producer after max retries")
                    raise

        try:
            async for msg in self.consumer:
                try:
                    data = json.loads(msg.value.decode())
                    self.batch.append(data)

                    if len(self.batch) >= self.batch_size:
                        await self._flush()

                except Exception as e:
                    logger.error(f"invalid_message: {e}")
                    await self._send_dlq(msg.value.decode(), e)

        finally:
            # Flush remaining batch before shutdown
            if self.batch:
                await self._flush()

            await self.consumer.stop()
            await self.dlq_producer.stop()

    async def _flush(self):
        try:
            logger.debug(f"Flushing batch of size {len(self.batch)}")

            await self.snowflake.insert_batch(self.batch)

            logger.info(f"Successfully flushed {len(self.batch)} events to Snowflake")

            await self.consumer.commit()
            self.batch.clear()

        except Exception as e:
            logger.error(f"snowflake_failed: {e}")

            for event in self.batch:
                await self._send_dlq(event, e)

            self.batch.clear()

    async def _send_dlq(self, data, reason):
        payload = {
            "original_event": data,
            "error_reason": str(reason),
            "failed_at": datetime.utcnow().isoformat()
        }

        await self.dlq_producer.send(TOPICS["dlq"], payload)

        logger.warning(f"Sent event to DLQ due to: {reason}")
        
if __name__ == "__main__":
    import asyncio
    # Create the class instance
    worker = SnowflakeConsumer()
    # Start the infinite listening loop
    asyncio.run(worker.start())