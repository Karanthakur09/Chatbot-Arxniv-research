import fitz  # PyMuPDF
from shared.logging import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        full_text = []

        for page in doc:
            text = page.get_text("text")
            if text:
                full_text.append(text)

        return "\n".join(full_text)

    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        raise