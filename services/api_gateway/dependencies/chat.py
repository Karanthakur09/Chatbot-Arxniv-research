# services/api_gateway/dependencies/chat.py
from core.chat.chat_service import ChatService
from services.api_gateway.producer import kafka_producer

# Import all the other tools your ChatService needs
from infra.ai.embeddings.local_embedder import LocalEmbedder
from infra.vector_db.qdrant_retriever import QdrantRetriever
from infra.ai.reranker.cross_encoder_reranker import CrossEncoderReranker
from infra.ai.llm.gateway_llm import GatewayLLM
from infra.cache.memory_adapter import MemoryAdapter
from core.chat.context_builder import ContextBuilder

def get_chat_service():
    # We build the "machine" here by plugging in all the parts
    return ChatService(
        embedder=LocalEmbedder(),
        retriever=QdrantRetriever(),
        reranker=CrossEncoderReranker(),
        llm=GatewayLLM(),
        memory=MemoryAdapter(),
        context_builder=ContextBuilder(),
        event_producer=kafka_producer  # <--- This comes from main.py
    )
