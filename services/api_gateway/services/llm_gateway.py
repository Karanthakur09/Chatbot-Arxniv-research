import time
import requests

from shared.config import settings
from shared.logging import get_logger

from services.api_gateway.services.llm import LLMClient  # Gemini

logger = get_logger(__name__)


class OpenRouterClient:

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def generate_answer(self, query, context):

        prompt = self._build_prompt(query, context)

        try:
            response = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": settings.LLM_TEMPERATURE,
                    "max_tokens": settings.LLM_MAX_TOKENS
                },
                timeout=10
            )

            response.raise_for_status()

            data = response.json()

            return data["choices"][0]["message"]["content"].strip()

        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            raise

    def _build_prompt(self, query, context):

        return f"""
You are a strict AI assistant.

STRICT RULES:
- Answer ONLY using the provided context
- DO NOT use outside knowledge
- DO NOT infer or assume anything
- Every statement MUST include citation in [doc_id]
- If the answer is not explicitly present, return EXACTLY:
  "Not found in context"

Context:
{context}

Question:
{query}

Answer:
"""


class LLMGateway:

    def __init__(self):

        self.primary = LLMClient()  # Gemini
        self.fallback = OpenRouterClient()

    def generate_answer(self, query, context):

        # 🔥 Retry for primary (Gemini)
        for attempt in range(2):
            try:
                start = time.time()

                answer = self.primary.generate_answer(query, context)

                latency = round(time.time() - start, 2)
                logger.info(f"llm=gemini latency={latency}s")

                if self._is_valid_answer(answer):
                    return answer

            except Exception as e:
                logger.warning(f"Gemini attempt {attempt+1} failed: {e}")
                time.sleep(1)

        # 🔥 Fallback → OpenRouter
        try:
            start = time.time()

            answer = self.fallback.generate_answer(query, context)

            latency = round(time.time() - start, 2)
            logger.info(f"llm=openrouter latency={latency}s")

            if self._is_valid_answer(answer):
                return answer

        except Exception as e:
            logger.error(f"OpenRouter failed: {e}")

        return "Not found in context"

    def _is_valid_answer(self, answer: str) -> bool:

        if not answer or len(answer.strip()) < 5:
            return False

        # enforce citation presence
        if "[" not in answer or "]" not in answer:
            return False

        return True