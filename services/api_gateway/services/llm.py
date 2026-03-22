# import time
# import os

# import google.generativeai as genai

# from shared.config import settings
# from shared.logging import get_logger

# logger = get_logger(__name__)


# class LLMClient:

#     def __init__(self, model_name=None):

#         self.api_key = settings.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY")
#         self.model_name = model_name or settings.GEMINI_MODEL

#         if not self.api_key:
#             raise ValueError("GEMINI_API_KEY not found")

#         genai.configure(api_key=self.api_key)

#         self.model = genai.GenerativeModel(self.model_name)

#     def generate_answer(self, query, context):

#         prompt = self._build_prompt(query, context)

#         try:
#             response = self.model.generate_content(
#                 prompt,
#                 generation_config={
#                     "temperature": settings.LLM_TEMPERATURE,
#                     "max_output_tokens": settings.LLM_MAX_TOKENS,
#                 }
#             )

#             if not response or not response.text:
#                 logger.warning("Empty response from Gemini")
#                 return "No answer generated."

#             return response.text.strip()

#         except Exception as e:
#             logger.error(f"Gemini API error: {e}")
#             return "LLM generation failed."

#         finally:
#             time.sleep(settings.GEMINI_RATE_LIMIT_SECONDS)

#     def _build_prompt(self, query, context):

#         return f"""
#             You are a strict AI assistant.

#             Answer ONLY from the provided context.
#             If the answer is not present, say: "Not found in context".

#             Context:
#             {context}

#             Question:
#             {query}

#             Answer:
#             """

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
    def generate_answer(self, query, context):

        prompt = self._build_prompt(query, context)

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
            
    def _build_prompt(self, query, context):

        return f"""
You are a strict AI assistant.

STRICT RULES:
- Answer ONLY using the provided context
- DO NOT use outside knowledge
- DO NOT infer or assume anything
- Every statement MUST include citation in [doc_id]
- If the answer is not explicitly stated in the context, return EXACTLY:
  "Not found in context"

- If context is insufficient → return "Not found in context"
- If unsure → return "Not found in context"

Context:
{context}

Question:
{query}

Answer:
"""
