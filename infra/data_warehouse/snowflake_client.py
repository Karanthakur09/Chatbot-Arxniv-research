import snowflake.connector
import time
import logging
from shared.config import settings

logger = logging.getLogger(__name__)


class SnowflakeClient:

    def __init__(self, max_retries: int = 5, initial_backoff: int = 2):
        """
        Initialize Snowflake client with retry logic.
        
        Args:
            max_retries: Number of connection attempts (default: 5)
            initial_backoff: Initial backoff in seconds (default: 2)
        """
        self.conn = None
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self._connect_with_retry()

    def _connect_with_retry(self):
        """Connect to Snowflake with exponential backoff retry logic."""
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Connecting to Snowflake (attempt {attempt}/{self.max_retries})")
                self.conn = snowflake.connector.connect(
                    user=settings.SNOWFLAKE_USER,
                    password=settings.SNOWFLAKE_PASSWORD,
                    account=settings.SNOWFLAKE_ACCOUNT,
                    warehouse=settings.SNOWFLAKE_WAREHOUSE,
                    database=settings.SNOWFLAKE_DATABASE,
                    schema=settings.SNOWFLAKE_SCHEMA,
                    login_timeout=10,
                    network_timeout=60,
                )
                logger.info("Successfully connected to Snowflake")
                return
            except Exception as e:
                logger.error(f"Snowflake connection failed (attempt {attempt}): {type(e).__name__}: {str(e)}")
                if attempt == self.max_retries:
                    logger.critical(f"Failed to connect to Snowflake after {self.max_retries} attempts")
                    raise
                backoff = self.initial_backoff ** (attempt - 1)
                logger.info(f"Retrying in {backoff} seconds...")
                time.sleep(backoff)

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