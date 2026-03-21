import uuid

def table_to_chunks(tables):

    chunks = []

    for table in tables:

        page = table.get("page")
        data = table.get("data", [])

        if not data or len(data) < 2:
            continue

        headers = data[0]

        for row in data[1:]:

            row_text_parts = []

            for h, cell in zip(headers, row):
                if h and cell:
                    row_text_parts.append(f"{h}: {cell}")

            if row_text_parts:
                chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "type": "table",
                    "content": ", ".join(row_text_parts),
                    "page": page
                })

    return chunks