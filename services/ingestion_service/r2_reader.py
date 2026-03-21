import boto3
from shared.config import settings
from shared.logging import get_logger

logger = get_logger(__name__)


class R2Reader:

    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT,
            aws_access_key_id=settings.R2_ACCESS_KEY,
            aws_secret_access_key=settings.R2_SECRET_KEY,
        )
        self.bucket = settings.R2_BUCKET

    def get_pdf(self, key: str) -> bytes:
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=key
            )
            return response["Body"].read()

        except Exception as e:
            logger.error(f"R2 read failed: {e}")
            raise