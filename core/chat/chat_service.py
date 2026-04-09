# import time
# import uuid
# import asyncio
# from datetime import datetime
# from typing import Any, Dict, List, AsyncGenerator
# from shared.schemas.event_schema import ChatEvent
# from shared.logging import get_logger

# logger = get_logger(__name__)


# class ChatService:
#     """
#     Core Chat Orchestration Layer (Async)
#     """

#     def __init__(
#         self,
#         embedder,
#         retriever,
#         reranker,
#         context_builder,
#         llm,
#         memory,
#         event_producer  
#     ):
#         self.embedder = embedder
#         self.retriever = retriever
#         self.reranker = reranker
#         self.context_builder = context_builder
#         self.llm = llm
#         self.memory = memory
#         self.event_producer = event_producer

#     # -----------------------------
#     # Helper Functions
#     # -----------------------------

#     def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
#         seen = set()
#         unique = []

#         for r in results:
#             content = r.get("content", "")
#             key = content[:200].strip()

#             if key in seen or not key:
#                 continue

#             seen.add(key)
#             unique.append(r)

#         return unique

#     def _diversify_results(self, results: List[Dict], max_per_doc: int = 2) -> List[Dict]:
#         doc_count = {}
#         diversified = []

#         for r in results:
#             doc_id = r.get("doc_id")

#             if doc_count.get(doc_id, 0) >= max_per_doc:
#                 continue

#             doc_count[doc_id] = doc_count.get(doc_id, 0) + 1
#             diversified.append(r)

#         return diversified

#     # -----------------------------
#     # Non-stream Chat
#     # -----------------------------

#     async def handle_chat(self, req: Any) -> Dict:
#         start_time = time.time()

#         try:
#             # 1. Memory
#             history = await self.memory.get_history(req.session_id)
#             history = history[-3:] if history else []

#             # 2. Embedding
#             query_vector = await self.embedder.embed(req.query)

#             # 3. Retrieval
#             results = await self.retriever.search(
#                 query_vector=query_vector,
#                 query_text=req.query,
#                 top_k=20,
#                 source=req.source,
#                 chunk_type=req.chunk_type
#             )

#             if not results:
#                 return {
#                     "query": req.query,
#                     "answer": "No relevant docs found.",
#                     "sources": []
#                 }

#             # 4. Rerank
#             if len(results) > 5:
#                 results = await self.reranker.rerank(req.query, results, req.top_k)
#             else:
#                 results = results[:req.top_k]

#             # 5. Clean & Context
#             results = self._deduplicate_results(results)
#             results = self._diversify_results(results, max_per_doc=2)
#             results = results[:req.top_k]

#             context = self.context_builder.build(results)

#             if not context or len(context.strip()) < 20:
#                 return {
#                     "query": req.query,
#                     "answer": "Not found in context",
#                     "sources": results
#                 }

#             # 6. LLM
#             answer = await self.llm.generate_answer(
#                 query=req.query,
#                 context=context,
#                 history=history
#             )

#             latency = round(time.time() - start_time, 3)

#             # 7. Save Memory
#             if answer and answer != "Not found in context" and "[" in answer:
#                 await self.memory.save(req.session_id, req.query, answer)

#             # 8. SEND KAFKA EVENT (Fire and Forget)
#             try:
#                 # 1. Create the data
#                 event_data = {
#                     "event_id": str(uuid.uuid4()),
#                     "session_id": req.session_id,
#                     "user_id": getattr(req, "user_id", None),
#                     "query": req.query,
#                     "response": full_answer,
#                     "latency": latency,
#                     "created_at": datetime.utcnow()
#                 }
                
#                  # 2. VERIFY: This line checks everything (types, missing fields, etc.)
#                 validated_event = ChatEvent(**event_data)

#                 # Use create_task to send in background without blocking the response
#                 asyncio.create_task(
#                     self.event_producer.send("chat_events", validated_event.model_dump())
#                 )

#                 logger.info(f"kafka_event_queued event_id={event['event_id']} latency={latency}s")

#             except Exception as kafka_error:
#                 logger.error(f"kafka_queue_failed error={kafka_error}")

#             return {
#                 "query": req.query,
#                 "answer": answer,
#                 "sources": results,
#                 "latency": latency
#             }

#         except Exception as e:
#             logger.error(f"chat_service_failed: {e}")
#             return {
#                 "query": req.query,
#                 "answer": "Internal error.",
#                 "sources": []
#             }

#     # -----------------------------
#     # Stream Chat
#     # -----------------------------

#     async def stream_chat(self, req: Any) -> AsyncGenerator[str, None]:
#         start_time = time.time()
#         full_answer = ""

#         try:
#             # 1. Memory
#             history = await self.memory.get_history(req.session_id)
#             history = history[-3:] if history else []

#             # 2. Embedding
#             query_vector = await self.embedder.embed(req.query)

#             # 3. Retrieval
#             results = await self.retriever.search(
#                 query_vector=query_vector,
#                 query_text=req.query,
#                 top_k=20,
#                 source=req.source,
#                 chunk_type=req.chunk_type
#             )

#             if not results:
#                 yield "No relevant docs found."
#                 return

#             # 4. Rerank
#             if len(results) > 5:
#                 results = await self.reranker.rerank(req.query, results, req.top_k)
#             else:
#                 results = results[:req.top_k]

#             # 5. Clean & Context
#             results = self._deduplicate_results(results)
#             results = self._diversify_results(results, max_per_doc=2)
#             results = results[:req.top_k]

#             context = self.context_builder.build(results)

#             if not context or len(context.strip()) < 20:
#                 yield "Not found in context"
#                 return

#             # 6. LLM Streaming
#             async for chunk in self.llm.stream_answer(
#                 query=req.query,
#                 context=context,
#                 history=history
#             ):
#                 if chunk:
#                     full_answer += chunk
#                     yield chunk

#             latency = round(time.time() - start_time, 3)

#             # 7. Save Memory
#             if full_answer and "Not found in context" not in full_answer and "[" in full_answer:
#                 await self.memory.save(req.session_id, req.query, full_answer)

#             # 8. SEND KAFKA EVENT (Fire and Forget)
#             try:
#                 event = {
#                     "event_id": str(uuid.uuid4()),
#                     "session_id": req.session_id,
#                     "user_id": getattr(req, "user_id", None),
#                     "query": req.query,
#                     "response": full_answer,
#                     "latency": latency,
#                     "created_at": datetime.utcnow().isoformat()
#                 }

#                 # Use create_task to send in background without blocking the stream end
#                 asyncio.create_task(
#                     self.event_producer.send("chat_events", event)
#                 )

#                 logger.info(f"kafka_event_queued event_id={event['event_id']} latency={latency}s")

#             except Exception as kafka_error:
#                 logger.error(f"kafka_queue_failed error={kafka_error}")

#         except Exception as e:
#             logger.error(f"stream_chat_failed: {e}")
#             yield "Internal server error."


import time
import uuid
import asyncio
from datetime import datetime
from typing import Any, Dict, List, AsyncGenerator
from shared.schemas.event_schema import ChatEvent
from shared.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """
    Core Chat Orchestration Layer (Async)
    """

    def __init__(
        self,
        embedder,
        retriever,
        reranker,
        context_builder,
        llm,
        memory,
        event_producer  
    ):
        self.embedder = embedder
        self.retriever = retriever
        self.reranker = reranker
        self.context_builder = context_builder
        self.llm = llm
        self.memory = memory
        self.event_producer = event_producer

    # -----------------------------
    # Helper Functions
    # -----------------------------

    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        seen = set()
        unique = []
        for r in results:
            content = r.get("content", "")
            key = content[:200].strip()
            if key in seen or not key:
                continue
            seen.add(key)
            unique.append(r)
        return unique

    def _diversify_results(self, results: List[Dict], max_per_doc: int = 2) -> List[Dict]:
        doc_count = {}
        diversified = []
        for r in results:
            doc_id = r.get("doc_id")
            if doc_count.get(doc_id, 0) >= max_per_doc:
                continue
            doc_count[doc_id] = doc_count.get(doc_id, 0) + 1
            diversified.append(r)
        return diversified

    # -----------------------------
    # Non-stream Chat
    # -----------------------------

    async def handle_chat(self, req: Any) -> Dict:
        start_time = time.time()

        try:
            # 1. Memory
            history = await self.memory.get_history(req.session_id)
            history = history[-3:] if history else []

            # 2. Embedding
            query_vector = await self.embedder.embed(req.query)

            # 3. Retrieval
            results = await self.retriever.search(
                query_vector=query_vector,
                query_text=req.query,
                top_k=20,
                source=req.source,
                chunk_type=req.chunk_type
            )

            if not results:
                return {"query": req.query, "answer": "No relevant docs found.", "sources": []}

            # 4. Rerank
            if len(results) > 5:
                results = await self.reranker.rerank(req.query, results, req.top_k)
            else:
                results = results[:req.top_k]

            # 5. Clean & Context
            results = self._deduplicate_results(results)
            results = self._diversify_results(results, max_per_doc=2)
            results = results[:req.top_k]

            context = self.context_builder.build(results)

            if not context or len(context.strip()) < 20:
                return {"query": req.query, "answer": "Not found in context", "sources": results}

            # 6. LLM
            answer = await self.llm.generate_answer(
                query=req.query,
                context=context,
                history=history
            )

            latency = round(time.time() - start_time, 3)

            # 7. Save Memory
            if answer and answer != "Not found in context" and "[" in answer:
                await self.memory.save(req.session_id, req.query, answer)

            # 8. SEND KAFKA EVENT (Fire and Forget)
            try:
                event_data = {
                    "event_id": str(uuid.uuid4()),
                    "session_id": req.session_id,
                    "user_id": getattr(req, "user_id", None),
                    "query": req.query,
                    "response": answer, # Fixed: was full_answer
                    "latency": latency,
                    "created_at": datetime.utcnow()
                }
                
                # Verify with Schema
                validated_event = ChatEvent(**event_data)

                asyncio.create_task(
                    self.event_producer.send("chat_events", validated_event.model_dump())
                )
                logger.info(f"kafka_event_queued event_id={event_data['event_id']}")

            except Exception as kafka_error:
                logger.error(f"kafka_queue_failed: {kafka_error}")

            return {
                "query": req.query,
                "answer": answer,
                "sources": results,
                "latency": latency
            }

        except Exception as e:
            logger.error(f"chat_service_failed: {e}")
            return {"query": req.query, "answer": "Internal error.", "sources": []}

    # -----------------------------
    # Stream Chat
    # -----------------------------

    async def stream_chat(self, req: Any) -> AsyncGenerator[str, None]:
        start_time = time.time()
        full_answer = ""

        try:
            # 1. Memory
            history = await self.memory.get_history(req.session_id)
            history = history[-3:] if history else []

            # 2. Embedding
            query_vector = await self.embedder.embed(req.query)

            # 3. Retrieval
            results = await self.retriever.search(
                query_vector=query_vector,
                query_text=req.query,
                top_k=20,
                source=req.source,
                chunk_type=req.chunk_type
            )

            if not results:
                yield "No relevant docs found."
                return

            # 4. Rerank
            if len(results) > 5:
                results = await self.reranker.rerank(req.query, results, req.top_k)
            else:
                results = results[:req.top_k]

            # 5. Clean & Context
            results = self._deduplicate_results(results)
            results = self._diversify_results(results, max_per_doc=2)
            results = results[:req.top_k]

            context = self.context_builder.build(results)

            if not context or len(context.strip()) < 20:
                yield "Not found in context"
                return

            # 6. LLM Streaming
            async for chunk in self.llm.stream_answer(
                query=req.query,
                context=context,
                history=history
            ):
                if chunk:
                    full_answer += chunk
                    yield chunk

            latency = round(time.time() - start_time, 3)

            # 7. Save Memory
            if full_answer and "Not found in context" not in full_answer and "[" in full_answer:
                await self.memory.save(req.session_id, req.query, full_answer)

            # 8. SEND KAFKA EVENT (Fire and Forget)
            try:
                event_data = {
                    "event_id": str(uuid.uuid4()),
                    "session_id": req.session_id,
                    "user_id": getattr(req, "user_id", None),
                    "query": req.query,
                    "response": full_answer,
                    "latency": latency,
                    "created_at": datetime.utcnow()
                }

                # Verify with Schema
                validated_event = ChatEvent(**event_data)

                asyncio.create_task(
                    self.event_producer.send("chat_events", validated_event.model_dump())
                )
                logger.info(f"kafka_event_queued event_id={event_data['event_id']}")

            except Exception as kafka_error:
                logger.error(f"kafka_queue_failed: {kafka_error}")

        except Exception as e:
            logger.error(f"stream_chat_failed: {e}")
            yield "Internal server error."
