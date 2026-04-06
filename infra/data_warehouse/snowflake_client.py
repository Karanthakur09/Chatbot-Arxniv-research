import snowflake.connector
from shared.config import settings


class SnowflakeClient:

    def __init__(self):
        self.conn = snowflake.connector.connect(
            user=settings.SNOWFLAKE_USER,
            password=settings.SNOWFLAKE_PASSWORD,
            account=settings.SNOWFLAKE_ACCOUNT,
            warehouse=settings.SNOWFLAKE_WAREHOUSE,
            database=settings.SNOWFLAKE_DATABASE,
            schema=settings.SNOWFLAKE_SCHEMA,
        )

    def insert_batch(self, records: list[dict]):
        query = """
        INSERT INTO chat_events (
            event_id, session_id, user_id, query, response, latency, created_at
        )
        VALUES (%(event_id)s, %(session_id)s, %(user_id)s, %(query)s,
                %(response)s, %(latency)s, %(created_at)s)
        """

        with self.conn.cursor() as cur:
            cur.executemany(query, records)