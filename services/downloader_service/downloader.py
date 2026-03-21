import requests
from shared.logging import get_logger

logger = get_logger(__name__)


def download_pdf_stream(url: str, timeout=30):

    headers = {
        "User-Agent": "enterprise-legal-ai/1.0"
    }

    session = requests.Session()

    try:
        response = session.get(url, headers=headers, stream=True, timeout=timeout)

        if response.status_code != 200:
            raise RuntimeError(f"Download failed: {response.status_code}")

        pdf_bytes = bytearray()

        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                pdf_bytes.extend(chunk)

        if not pdf_bytes:
            raise ValueError("Empty PDF")

        return bytes(pdf_bytes)

    except Exception as e:
        logger.error(f"Download error: {e}")
        raise