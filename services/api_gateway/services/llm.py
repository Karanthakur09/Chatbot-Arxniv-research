
from google import genai
import os
import time

from shared.config import settings
from shared.logging import get_logger

logger = get_logger(__name__)


class LLMClient:

    def __init__(self, model_name=None):

        self.api_key = settings.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name or settings.GEMINI_MODEL

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found")

        self.client = genai.Client(api_key=self.api_key)

    # def generate_answer(self, query, context):

    #     prompt = self._build_prompt(query, context)

    #     try:
    #         response = self.client.models.generate_content(
    #             model=self.model_name,
    #             contents=prompt,
    #             config={
    #                 "temperature": settings.LLM_TEMPERATURE,
    #                 "max_output_tokens": settings.LLM_MAX_TOKENS,
    #             }
    #         )

    #         if not response or not response.text:
    #             logger.warning("Empty response from Gemini")
    #             return "No answer generated."

    #         return response.text.strip()

    #     except Exception as e:
    #         logger.error(f"Gemini API error: {e}")
    #         return "LLM generation failed."

    #     finally:
    #         time.sleep(1)
    def generate_answer(self, query, context, history=None):

        prompt = self._build_prompt(query, context,history)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "temperature": settings.LLM_TEMPERATURE,
                    "max_output_tokens": settings.LLM_MAX_TOKENS,
                }
            )

            if not response or not response.text:
                return "Not found in context"

            answer = response.text.strip()

            # 🔥 Guard 1: force fallback if suspicious
            if len(answer) < 5:
                return "Not found in context"

            # 🔥 Guard 2: enforce citation presence
            if "[" not in answer or "]" not in answer:
                return "Not found in context"

            return answer

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "LLM generation failed."      
    
    def _build_prompt(self, query, context, history=None):

        history_text = ""

        if history:
            for h in history:
                history_text += f"Q: {h['query']}\nA: {h['answer']}\n"

        return f"""
    You are a strict AI assistant.

    Use conversation history if relevant.

    STRICT RULES:
    - Answer ONLY using provided context
    - Use history only for understanding question
    - DO NOT use outside knowledge
    - If not found → "Not found in context"

    Conversation History:
    {history_text}

    Context:
    {context}

    Question:
    {query}

    Answer:
    """