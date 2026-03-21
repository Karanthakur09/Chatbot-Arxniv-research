import uuid

def chunk_text(text: str, chunk_size=500, overlap=100):

    paragraphs = text.split("\n")

    chunks = []
    current_chunk = []
    current_len = 0

    for para in paragraphs:

        words = para.split()
        if not words:
            continue

        if current_len + len(words) > chunk_size:
            chunk_text = " ".join(current_chunk)

            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "type": "text",
                "content": chunk_text
            })

            # overlap
            current_chunk = current_chunk[-overlap:]
            current_len = len(current_chunk)

        current_chunk.extend(words)
        current_len += len(words)

    if current_chunk:
        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "type": "text",
            "content": " ".join(current_chunk)
        })

    return chunks