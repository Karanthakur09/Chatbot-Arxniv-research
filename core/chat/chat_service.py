import time
from typing import Any, Dict, List, AsyncGenerator

from shared.logging import get_logger

logger = get_logger(__name__)

class ChatService:
    """
    Core Chat Orchestration Layer (Async)
    
    Responsibilities:
    - Orchestrate retrieval + rerank + context + LLM
    - Handle memory interaction
    - Keep API layer thin
    """
    
    def __init__(
        self,
        embedder,
        retriever,
        reranker,
        context_builder,
        llm,
        memory
    ):
        self.embedder = embedder
        self.retriever = retriever
        self.reranker = reranker
        self.context_builder = context_builder
        self.llm = llm
        self.memory = memory

    # Helper Functions (Sync - only process data)
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate results"""
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
        """Limit results per document"""
        doc_count = {}
        diversified = []
        
        for r in results:
            doc_id = r.get("doc_id")
            
            if doc_count.get(doc_id, 0) >= max_per_doc:
                continue
            
            doc_count[doc_id] = doc_count.get(doc_id, 0) + 1
            diversified.append(r)
        
        return diversified

    # Main Handlers (Async)
    
    async def handle_chat(self, req: Any) -> Dict:
        """Async handle chat request with generate_answer"""
        start_time = time.time()

        try:
            # 1. Memory
            history = await self.memory.get_history(req.session_id)
            history = history[-3:] if history else []

            logger.info(f"history_length={len(history)}")

            # 2. Embedding
            embed_start = time.time()
            query_vector = await self.embedder.embed(req.query)
            embed_time = round(time.time() - embed_start, 3)

            logger.info(f"embed_time={embed_time}s")

            # 3. Retrieval
            retrieval_start = time.time()
            results = await self.retriever.search(
                query_vector=query_vector,
                query_text=req.query,
                top_k=20,
                source=req.source,
                chunk_type=req.chunk_type
            )

            if not results:
                return {
                    "query": req.query,
                    "answer": "No relevant docs found.",
                    "sources": []
                }

            retrieval_time = round(time.time() - retrieval_start, 3)
            logger.info(f"retrieval_time={retrieval_time}s results={len(results)}")

            # 4. Rerank
            rerank_start = time.time()

            if len(results) > 5:
                logger.info(f"reranking_enabled=true count={len(results)}")
                results = await self.reranker.rerank(req.query, results, req.top_k)
            else:
                logger.info("reranking_skipped=true")
                results = results[:req.top_k]

            rerank_time = round(time.time() - rerank_start, 3)
            logger.info(f"rerank_time={rerank_time}s")

            # 5. Clean Results
            results = self._deduplicate_results(results)
            results = self._diversify_results(results, max_per_doc=2)
            results = results[:req.top_k]

            # 6. Context Build
            context = self.context_builder.build(results)

            if not context or len(context.strip()) < 20:
                return {
                    "query": req.query,
                    "answer": "Not found in context",
                    "sources": results
                }

            # 7. LLM
            llm_start = time.time()

            answer = await self.llm.generate_answer(
                query=req.query,
                context=context,
                history=history
            )

            llm_time = round(time.time() - llm_start, 3)
            total_time = round(time.time() - start_time, 3)

            logger.info(
                f"query='{req.query}' total_time={total_time}s llm_time={llm_time}s"
            )

            # 8. Save Memory (Background task in routes)
            if answer and answer != "Not found in context" and "[" in answer:
                await self.memory.save(req.session_id, req.query, answer)

            return {
                "query": req.query,
                "answer": answer,
                "sources": results,
                "latency": total_time
            }

        except Exception as e:
            logger.error(f"chat_service_failed query='{req.query}' error={e}")
            return {
                "query": req.query,
                "answer": "Internal server error.",
                "sources": []
            }
    
    async def stream_chat(self, req: Any) -> AsyncGenerator[str, None]:
        """Async stream chat response"""
        start_time = time.time()
        full_answer = ""
        results = []

        try:
            # 1. Memory
            history = await self.memory.get_history(req.session_id)
            history = history[-3:] if history else []
            logger.info(f"stream_history_length={len(history)}")

            # 2. Embedding
            embed_start = time.time()
            query_vector = await self.embedder.embed(req.query)
            logger.info(f"stream_embed_time={round(time.time() - embed_start, 3)}s")

            # 3. Retrieval
            retrieval_start = time.time()
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

            logger.info(f"stream_retrieval_time={round(time.time() - retrieval_start, 3)}s results={len(results)}")

            # 4. Rerank
            rerank_start = time.time()
            if len(results) > 5:
                results = await self.reranker.rerank(req.query, results, req.top_k)
                logger.info(f"stream_rerank_time={round(time.time() - rerank_start, 3)}s")
            else:
                results = results[:req.top_k]

            # 5. Clean Results
            results = self._deduplicate_results(results)
            results = self._diversify_results(results, max_per_doc=2)
            results = results[:req.top_k]

            # 6. Context Build
            context = self.context_builder.build(results)
            if not context or len(context.strip()) < 20:
                yield "Not found in context"
                return

            # 7. LLM Streaming
            llm_start = time.time()
            
            # Stream chunks
            async for chunk in self.llm.stream(req.query, context, history):
                if chunk:
                    full_answer += chunk
                    yield chunk

            llm_time = round(time.time() - llm_start, 3)
            total_time = round(time.time() - start_time, 3)
            logger.info(f"stream_complete query='{req.query}' total={total_time}s llm={llm_time}s")

            # 8. Save Memory (Matches your logic)
            if full_answer and "Not found in context" not in full_answer and "[" in full_answer:
                await self.memory.save(req.session_id, req.query, full_answer)

        except Exception as e:
            logger.error(f"stream_chat_failed query='{req.query}' error={e}")
            yield "Internal server error."

    # -----------------------------
    # Main Handler (Now Async)
    # -----------------------------

    async def handle_chat(self, req: Any) -> Dict:
        start_time = time.time()

        try:
            # 1. Memory (AWAITED)
            history = await self.memory.get_history(req.session_id)
            history = history[-3:] if history else []

            # 2. Embedding (AWAITED)
            query_vector = await self.embedder.embed(req.query)

            # 3. Retrieval (AWAITED)
            results = await self.retriever.search(
                query_vector=query_vector,
                query_text=req.query,
                top_k=20,
                source=req.source,
                chunk_type=req.chunk_type
            )

            if not results:
                return {"query": req.query, "answer": "No relevant docs found.", "sources": []}

            # 4. Rerank (AWAITED)
            if len(results) > 5:
                results = await self.reranker.rerank(req.query, results, req.top_k)
            else:
                results = results[:req.top_k]

            # 5. Clean & Context (Sync logic)
            results = self._deduplicate_results(results)
            results = self._diversify_results(results, max_per_doc=2)
            results = results[:req.top_k]
            context = self.context_builder.build(results)

            if not context or len(context.strip()) < 20:
                return {"query": req.query, "answer": "Not found in context", "sources": results}

            # 7. LLM (AWAITED)
            answer = await self.llm.generate_answer(
                query=req.query,
                context=context,
                history=history
            )

            # 8. Save Memory (AWAITED)
            # Note: In your route, you use BackgroundTasks for this, 
            # but we keep it here for safety or if called directly.
            if answer and answer != "Not found in context" and "[" in answer:
                await self.memory.save(req.session_id, req.query, answer)

            return {
                "query": req.query,
                "answer": answer,
                "sources": results,
                "latency": round(time.time() - start_time, 3)
            }

        except Exception as e:
            logger.error(f"chat_service_failed: {e}")
            return {"query": req.query, "answer": "Internal error.", "sources": []}
    
    # -----------------------------
    # Stream Handler (Now Async Generator)
    # -----------------------------

    async def stream_chat(self, req: Any) -> AsyncGenerator[str, None]:
        start_time = time.time()
        full_answer = ""

        try:
            # 1-3. Retrieval Flow (AWAITED)
            history = await self.memory.get_history(req.session_id)
            history = history[-3:] if history else []
            
            query_vector = await self.embedder.embed(req.query)
            
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

            # 4. Rerank (AWAITED)
            if len(results) > 5:
                results = await self.reranker.rerank(req.query, results, req.top_k)
            else:
                results = results[:req.top_k]

            # 5-6. Clean & Context
            results = self._deduplicate_results(results)
            results = self._diversify_results(results, max_per_doc=2)
            results = results[:req.top_k]
            context = self.context_builder.build(results)
            
            if not context or len(context.strip()) < 20:
                yield "Not found in context"
                return

            # 7. LLM Streaming (ASYNC FOR)
            # Since llm.stream_answer is now an async generator
            async for chunk in self.llm.stream_answer(
                query=req.query,
                context=context,
                history=history
            ):
                if chunk:
                    full_answer += chunk
                    yield chunk

            # 8. Save Memory (AWAITED)
            if full_answer and "Not found in context" not in full_answer and "[" in full_answer:
                await self.memory.save(req.session_id, req.query, full_answer)

        except Exception as e:
            logger.error(f"stream_chat_failed: {e}")
            yield "Internal server error."
