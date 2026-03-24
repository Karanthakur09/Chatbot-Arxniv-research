import time
from typing import Any, Dict, List

from shared.logging import get_logger


logger = get_logger(__name__)


class ChatService:
    """
    Core Chat Orchestration Layer

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
    # Main Handler
    # -----------------------------

    def handle_chat(self, req: Any) -> Dict:
        start_time = time.time()

        try:
            # 1. Memory
            history = self.memory.get_history(req.session_id)
            history = history[-3:] if history else []

            logger.info(f"history_length={len(history)}")

            # 2. Embedding
            embed_start = time.time()
            query_vector = self.embedder.embed(req.query)
            embed_time = round(time.time() - embed_start, 3)

            logger.info(f"embed_time={embed_time}s")

            # 3. Retrieval
            retrieval_start = time.time()

            results = self.retriever.search(
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
                results = self.reranker.rerank(req.query, results, req.top_k)
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

            answer = self.llm.generate_answer(
                query=req.query,
                context=context,
                history=history
            )

            llm_time = round(time.time() - llm_start, 3)

            total_time = round(time.time() - start_time, 3)

            logger.info(
                f"query='{req.query}' total_time={total_time}s llm_time={llm_time}s"
            )

            # 8. Save Memory
            if answer and answer != "Not found in context" and "[" in answer:
                self.memory.save(req.session_id, req.query, answer)

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