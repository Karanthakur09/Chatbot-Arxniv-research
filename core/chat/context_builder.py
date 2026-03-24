# import tiktoken

# from shared.config import settings
# from shared.logging import get_logger

# logger = get_logger(__name__)


# class ContextBuilder:

#     def __init__(self, max_tokens=None):
#         self.max_tokens = max_tokens or settings.CONTEXT_MAX_TOKENS

#         # ✅ tokenizer (fast + reusable)
#         self.tokenizer = tiktoken.get_encoding("cl100k_base")

#     def _count_tokens(self, text: str) -> int:
#         return len(self.tokenizer.encode(text))

#     def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
#         tokens = self.tokenizer.encode(text)
#         return self.tokenizer.decode(tokens[:max_tokens])

#     def build(self, results):

#         context_parts = []
#         total_tokens = 0

#         for r in results:

#             try:
#                 doc_id = r.get("doc_id", "unknown")

#                 content = (
#                     r.get("content") or
#                     r.get("text") or
#                     r.get("chunk") or
#                     ""
#                 ).strip()

#                 if not content:
#                     continue

#                 # 🔥 attach source id (for citations later)
#                 content = f"[{doc_id}] {content}"

#                 content_tokens = self._count_tokens(content)

#                 # 🔥 truncate if single chunk too big
#                 if content_tokens > self.max_tokens:
#                     content = self._truncate_to_tokens(content, self.max_tokens)
#                     content_tokens = self._count_tokens(content)

#                 if total_tokens + content_tokens > self.max_tokens:
#                     break

#                 context_parts.append(content)
#                 total_tokens += content_tokens

#             except Exception as e:
#                 logger.warning(f"Context build error: {e}")
#                 continue

#         if not context_parts:
#             logger.warning("Empty context generated")

#         logger.info(f"context_tokens={total_tokens}")

#         return "\n\n".join(context_parts)
import tiktoken

from shared.config import settings
from shared.logging import get_logger

logger = get_logger(__name__)


class ContextBuilder:

    def __init__(self, max_tokens=None):
        self.max_tokens = max_tokens or settings.CONTEXT_MAX_TOKENS

        # tokenizer (fast + reusable)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        tokens = self.tokenizer.encode(text)
        return self.tokenizer.decode(tokens[:max_tokens])

    def build(self, results):

        context_parts = []
        total_tokens = 0

        for r in results:
            try:
                doc_id = r.get("doc_id", "unknown")

                content = (
                    r.get("content") or
                    r.get("text") or
                    r.get("chunk") or
                    ""
                ).strip()

                if not content:
                    continue

                content = f"[{doc_id}] {content}"
                content_tokens = self._count_tokens(content)

                remaining_tokens = self.max_tokens - total_tokens

                if remaining_tokens <= 0:
                    break

                if content_tokens > remaining_tokens:
                    content = self._truncate_to_tokens(content, remaining_tokens)
                    content_tokens = self._count_tokens(content)

                context_parts.append(content)
                total_tokens += content_tokens

            except Exception as e:
                logger.warning(f"Context build error: {e}")
                continue
        
        logger.info(f"context_tokens={total_tokens}")
                    
        if not context_parts:
            logger.warning("Empty context generated")

        logger.info(f"context_tokens={total_tokens}")

        return "\n\n".join(context_parts)