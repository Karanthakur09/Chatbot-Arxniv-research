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

        create_temp_table = """
        CREATE TEMP TABLE IF NOT EXISTS temp_chat_events LIKE chat_events;
        """

        insert_query = """
        INSERT INTO temp_chat_events (
            event_id, session_id, user_id, query, response, latency, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        """

        merge_query = """
        MERGE INTO chat_events AS target
        USING temp_chat_events AS source
        ON target.event_id = source.event_id
        WHEN NOT MATCHED THEN
            INSERT (
                event_id, session_id, user_id, query, response, latency, created_at
            )
            VALUES (
                source.event_id, source.session_id, source.user_id,
                source.query, source.response, source.latency, source.created_at
            );
        """

        # convert dict → tuple
        tuple_records = [
            (
                r["event_id"],
                r["session_id"],
                r["user_id"],
                r["query"],
                r["response"],
                r["latency"],
                r["created_at"]
            )
            for r in records
        ]

        with self.conn.cursor() as cur:
            cur.execute(create_temp_table)
            cur.executemany(insert_query, tuple_records)
            cur.execute(merge_query)