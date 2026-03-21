import pdfplumber
import io
from shared.logging import get_logger

logger = get_logger(__name__)


def extract_tables_from_pdf(pdf_bytes: bytes):

    tables_output = []

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:

            for page_number, page in enumerate(pdf.pages):

                tables = page.extract_tables()

                if not tables:
                    continue

                for table in tables:

                    # Clean table rows
                    cleaned_table = []

                    for row in table:
                        if not row:
                            continue

                        cleaned_row = [
                            cell.strip() if cell else ""
                            for cell in row
                        ]

                        # skip empty rows
                        if any(cleaned_row):
                            cleaned_table.append(cleaned_row)

                    if cleaned_table:
                        tables_output.append({
                            "page": page_number,
                            "data": cleaned_table
                        })

        return tables_output

    except Exception as e:
        logger.error(f"Table extraction failed: {e}")
        return []
    
    
### Data will be outputed in this format
# [
#   {
#     "page": 2,
#     "data": [
#       ["Name", "Age"],
#       ["John", "25"]
#     ]
#   }
# ]
###