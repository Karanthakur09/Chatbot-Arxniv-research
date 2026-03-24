import requests

from shared.config import settings
from shared.logging import get_logger

logger = get_logger(__name__)


class OpenRouterClient:

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def generate(self, prompt: str) -> str:

        try:
            response = requests.post(
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

            response.raise_for_status()

            return response.json()["choices"][0]["message"]["content"].strip()

        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            return ""