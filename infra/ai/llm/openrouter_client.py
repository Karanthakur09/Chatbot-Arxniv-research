import requests
import json
import asyncio

from shared.config import settings
from shared.logging import get_logger

logger = get_logger(__name__)


class OpenRouterClient:

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    async def generate(self, prompt: str) -> str:
        """Async generate using thread pool"""
        try:
            # Run blocking HTTP call in thread pool
            response = await asyncio.to_thread(
                lambda: requests.post(
                    self.url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": settings.LLM_TEMPERATURE,
                        "max_tokens": settings.LLM_MAX_TOKENS
                    },
                    timeout=15
                )
            )

            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()

        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            return ""

    async def stream(self, prompt: str):
        """Async stream generation using thread pool"""
        try:
            # Run blocking HTTP call in thread pool
            response = await asyncio.to_thread(
                lambda: requests.post(
                    self.url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": settings.LLM_TEMPERATURE,
                        "max_tokens": settings.LLM_MAX_TOKENS,
                        "stream": True
                    },
                    stream=True,
                    timeout=30
                )
            )

            for line in response.iter_lines():
                if line:
                    decoded = line.decode("utf-8")

                    if decoded.startswith("data: "):
                        data = decoded[6:]

                        if data == "[DONE]":
                            break

                        try:
                            json_data = json.loads(data)
                            delta = json_data["choices"][0]["delta"].get("content")

                            if delta:
                                yield delta
                        except Exception:
                            continue

        except Exception as e:
            logger.error(f"OpenRouter streaming error: {e}")
            yield "[ERROR]"