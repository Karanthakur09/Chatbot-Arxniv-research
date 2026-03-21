import boto3
from shared.logging import get_logger
from shared.config import settings
logger = get_logger(__name__)

class R2Client:

    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT,
            aws_access_key_id=settings.R2_ACCESS_KEY,
            aws_secret_access_key=settings.R2_SECRET_KEY
        )
        self.bucket = settings.R2_BUCKET

    def upload_pdf(self, key: str, data: bytes):

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType="application/pdf"
            )
            return True

        except Exception as e:
            logger.error(f"R2 upload failed: {e}")
            return False