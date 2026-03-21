from qdrant_client.models import PointStruct
import uuid

from services.embedding_service.qdrant_client import client, COLLECTION_NAME


def store_embeddings(doc_id, chunks, embeddings, source):

    points = []

    for chunk, vector in zip(chunks, embeddings):

        payload = {
            "doc_id": doc_id,
            "chunk_id": chunk["chunk_id"],
            "type": chunk["type"],
            "content": chunk["content"],
            "source": source,  # text / ocr
            "page": chunk.get("page")
        }

        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector.tolist(),
                payload=payload
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )