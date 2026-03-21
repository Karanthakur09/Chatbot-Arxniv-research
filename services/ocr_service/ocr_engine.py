import pytesseract
from pdf2image import convert_from_bytes
from shared.logging import get_logger

logger = get_logger(__name__)


def extract_text_via_ocr(pdf_bytes: bytes):

    try:
        images = convert_from_bytes(pdf_bytes)

        text_output = []

        for img in images:
            text = pytesseract.image_to_string(img)
            if text:
                text_output.append(text)

        return "\n".join(text_output)

    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise