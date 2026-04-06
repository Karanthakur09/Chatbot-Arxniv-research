import asyncio
from concurrent.futures import ThreadPoolExecutor
from infra.data_warehouse.snowflake_client import SnowflakeClient

executor = ThreadPoolExecutor(max_workers=5)


class SnowflakeAsyncService:

    def __init__(self):
        self.client = SnowflakeClient()

    async def insert_batch(self, records: list[dict]):
        loop = asyncio.get_event_loop()

        await loop.run_in_executor(
            executor,
            self.client.insert_batch,
            records
        )