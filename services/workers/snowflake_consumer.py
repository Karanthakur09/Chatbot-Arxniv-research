# import json
# from aiokafka import AIOKafkaConsumer

# from infra.data_warehouse.snowflake_async import SnowflakeAsyncService
# from infra.event_bus.kafka_config import TOPICS
# from infra.event_bus.kafka_producer import KafkaProducerService

# from shared.logging import get_logger

# logger = get_logger(__name__)


# class SnowflakeConsumer:

#     def __init__(self):
#         self.consumer = AIOKafkaConsumer(
#             TOPICS["chat_events"],
#             bootstrap_servers="localhost:9092",
#             group_id="snowflake-group",
#             enable_auto_commit=False
#         )

#         self.snowflake = SnowflakeAsyncService()
#         self.batch = []
#         self.batch_size = 20

#         self.dlq_producer = KafkaProducerService() # DLQ

#     async def start(self):
#         await self.consumer.start()
#         await self.dlq_producer.start()

#         try:
#             async for msg in self.consumer:
#                 try:
#                     data = json.loads(msg.value.decode())
#                     self.batch.append(data)

#                     if len(self.batch) >= self.batch_size:
#                         await self._flush()
                        
                        
#                 except Exception as e:
#                     logger.error(f"invalid_message: {e}")
#                     await self._send_dlq(msg.value)

#         finally:
#             await self.consumer.stop()
#             await self.dlq_producer.stop()

#     async def _flush(self):
#         try:
#             await self.snowflake.insert_batch(self.batch)
#             logger.info(f"Successfully flushed {len(self.batch)} events to Snowflake")
#             await self.consumer.commit()
#             self.batch.clear()

#         except Exception as e:
#             logger.error(f"snowflake_failed: {e}")

#             for event in self.batch:
#                 await self._send_dlq(event)

#             self.batch.clear()

#     async def _send_dlq(self, data, reason):
#         payload = {
#             "original_event": data,
#             "error_reason": str(reason),
#             "failed_at": datetime.utcnow().isoformat()
#         }

#         await self.dlq_producer.send(TOPICS["dlq"], payload)
#         logger.warning(f"Sent event to DLQ due to: {reason}")

import json
from datetime import datetime

from aiokafka import AIOKafkaConsumer

from infra.data_warehouse.snowflake_async import SnowflakeAsyncService
from infra.event_bus.kafka_config import TOPICS
from infra.event_bus.kafka_producer import KafkaProducerService

from shared.logging import get_logger

logger = get_logger(__name__)


class SnowflakeConsumer:

    def __init__(self):
        self.consumer = AIOKafkaConsumer(
            TOPICS["chat_events"],
            bootstrap_servers="localhost:9092",
            group_id="snowflake-group",
            enable_auto_commit=False
        )

        self.snowflake = SnowflakeAsyncService()
        self.batch = []
        self.batch_size = 20

        self.dlq_producer = KafkaProducerService()  # DLQ

    async def start(self):
        await self.consumer.start()
        await self.dlq_producer.start()

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