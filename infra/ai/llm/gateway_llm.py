from typing import List, Dict
import time

from core.ai.llm.base import BaseLLM
from shared.logging import get_logger

from infra.ai.llm.gemini_client import GeminiClient
from infra.ai.llm.openrouter_client import OpenRouterClient

logger = get_logger(__name__)


class GatewayLLM(BaseLLM):

    def __init__(self):
        self.primary = GeminiClient()
        self.fallback = OpenRouterClient()

    def generate_answer(
        self,
        query: str,
        context: str,
        history: List[Dict]
    ) -> str:

        prompt = self._build_prompt(query, context, history)

        # Primary
        for attempt in range(2):
            try:
                start = time.time()
                answer = self.primary.generate(prompt)

                if self._valid(answer):
                    logger.info(f"llm=gemini latency={round(time.time()-start,2)}s")
                    return answer

            except Exception as e:
                logger.warning(f"Gemini failed: {e}")

        # Fallback
        try:
            answer = self.fallback.generate(prompt)
            if self._valid(answer):
                return answer
        except Exception as e:
            logger.error(f"Fallback failed: {e}")

        return "Not found in context"

    def _valid(self, answer: str) -> bool:
        if not answer:
            return False

        clean = answer.strip().lower()

        if "not found in context" in clean:
            return False

        if len(clean) < 30:
            return False

        return True

    def _build_prompt(self, query, context, history):

        history_text = ""
        if history:
            for h in history:
                history_text += f"Q: {h['query']}\nA: {h['answer']}\n"

        return f"""
    You are an expert AI assistant.

    STRICT RULES:
    - Answer ONLY using the provided context
    - DO NOT use outside knowledge
    - If answer not found → say "Not found in context"

    IMPORTANT:
    - Provide a DETAILED and EXPLANATORY answer
    - Do not just list points — explain them clearly
    - Expand each point with reasoning or examples from context
    - Write in a structured and complete manner

    Conversation History:
    {history_text}

    Context:
    {context}

    Question:
    {query}

    Detailed Answer:
    """
    
    def stream_answer(self, query: str, context: str, history):

        prompt = self._build_prompt(query, context, history)

        # Primary (Gemini)
        try:
            for chunk in self.primary.stream(prompt):
                yield chunk
            return
        except Exception as e:
            logger.warning(f"Gemini stream failed: {e}")

        # Fallback (OpenRouter)
        try:
            for chunk in self.fallback.stream(prompt):
                yield chunk
        except Exception as e:
            logger.error(f"Fallback stream failed: {e}")
            yield "[ERROR]"    