from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from shared.config import settings

client = QdrantClient(
    host=settings.QDRANT_HOST,
    port=settings.QDRANT_PORT
)

COLLECTION_NAME = "documents"


def init_collection():

    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=384,  # for all-MiniLM-L6-v2
            distance=Distance.COSINE
        )
    )