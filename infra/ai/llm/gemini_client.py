from google import genai
import os
import asyncio

from shared.config import settings
from shared.logging import get_logger

logger = get_logger(__name__)


class GeminiClient:

    def __init__(self):
        api_key = settings.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")

        self.client = genai.Client(api_key=api_key)
        self.model = settings.GEMINI_MODEL

    async def generate(self, prompt: str) -> str:
        """Async generate using thread pool"""
        try:
            # Run blocking API call in thread pool
            response = await asyncio.to_thread(
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "temperature": settings.LLM_TEMPERATURE,
                        "max_output_tokens": settings.LLM_MAX_TOKENS,
                    }
                )
            )
            return response.text.strip() if response and response.text else ""

        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return ""

    async def stream(self, prompt: str):
        """Async stream generation"""
        try:
            # Run blocking API call in thread pool
            stream = await asyncio.to_thread(
                lambda: self.client.models.generate_content_stream(
                    model=self.model,
                    contents=prompt,
                    config={
                        "temperature": settings.LLM_TEMPERATURE,
                        "max_output_tokens": settings.LLM_MAX_TOKENS,
                    }
                )
            )

            for chunk in stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            yield "[ERROR]"