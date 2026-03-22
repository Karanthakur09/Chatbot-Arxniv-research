# import time
# import requests

# from shared.config import settings
# from shared.logging import get_logger

# from services.api_gateway.services.llm import LLMClient  # Gemini

# logger = get_logger(__name__)


# class OpenRouterClient:

#     def __init__(self):
#         self.api_key = settings.OPENROUTER_API_KEY
#         self.model = settings.OPENROUTER_MODEL
#         self.url = "https://openrouter.ai/api/v1/chat/completions"

#     def generate_answer(self, query, context ,history=None):

#         prompt = self._build_prompt(query, context,history)

#         try:
#             response = requests.post(
#                 self.url,
#                 headers={
#                     "Authorization": f"Bearer {self.api_key}",
#                     "Content-Type": "application/json"
#                 },
#                 json={
#                     "model": self.model,
#                     "messages": [
#                         {"role": "user", "content": prompt}
#                     ],
#                     "temperature": settings.LLM_TEMPERATURE,
#                     "max_tokens": settings.LLM_MAX_TOKENS
#                 },
#                 timeout=10
#             )

#             response.raise_for_status()

#             data = response.json()

#             return data["choices"][0]["message"]["content"].strip()

#         except Exception as e:
#             logger.error(f"OpenRouter API error: {e}")
#             raise

#     def _build_prompt(self, query, context, history=None):

#         history_text = ""

#         if history:
#             for h in history:
#                 history_text += f"Q: {h['query']}\nA: {h['answer']}\n"

#         return f"""
#     You are a strict AI assistant.

#     Use conversation history if relevant.

#     STRICT RULES:
#     - Answer ONLY using provided context
#     - Use history only for understanding question
#     - DO NOT use outside knowledge
#     - If not found → "Not found in context"

#     Conversation History:
#     {history_text}

#     Context:
#     {context}

#     Question:
#     {query}

#     Answer:
#     """


# class LLMGateway:

#     def __init__(self):

#         self.primary = LLMClient()  # Gemini
#         self.fallback = OpenRouterClient()

#     def generate_answer(self, query, context, history=None):

#         # 🔥 Retry for primary (Gemini)
#         for attempt in range(2):
#             try:
#                 start = time.time()

#                 answer = self.primary.generate_answer(query, context, history=None)

#                 latency = round(time.time() - start, 2)
#                 logger.info(f"llm=gemini latency={latency}s")

#                 if self._is_valid_answer(answer):
#                     return answer

#             except Exception as e:
#                 logger.warning(f"Gemini attempt {attempt+1} failed: {e}")
#                 time.sleep(1)

#         # 🔥 Fallback → OpenRouter
#         try:
#             start = time.time()

#             answer = self.fallback.generate_answer(query, context,history=None)

#             latency = round(time.time() - start, 2)
#             logger.info(f"llm=openrouter latency={latency}s")

#             if self._is_valid_answer(answer):
#                 return answer

#         except Exception as e:
#             logger.error(f"OpenRouter failed: {e}")

#         return "Not found in context"

#     def _is_valid_answer(self, answer: str) -> bool:
#         if not answer:
#             return False
        
#         clean_answer = answer.strip().lower()
        
#         # Block standard "I don't know" responses
#         if "not found in context" in clean_answer or "i do not have enough information" in clean_answer:
#             return False
            
#         if len(clean_answer) < 10:
#             return False

#         # Optional: Keep citation check but maybe log it instead of failing
#         if "[" not in answer:
#             logger.debug("Answer missing citations, but allowing through.")
            
#         return True

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

    def generate_answer(self, query, context, history=None):
        # FIX: Pass the history to the prompt builder
        prompt = self._build_prompt(query, context, history)

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
                timeout=15 # Increased timeout slightly for history processing
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            raise

    def _build_prompt(self, query, context, history=None):
        history_text = ""
        if history:
            for h in history:
                history_text += f"User: {h['query']}\nAI: {h['answer']}\n"

        return f"""You are a strict AI assistant. Answer ONLY using provided context. 

Conversation History:
{history_text}

Context:
{context}

Question:
{query}

Answer:"""

class LLMGateway:
    def __init__(self):
        self.primary = LLMClient()
        self.fallback = OpenRouterClient()

    def generate_answer(self, query, context, history=None):
        # 🔥 FIX: Pass 'history' instead of 'None'
        for attempt in range(2):
            try:
                start = time.time()
                answer = self.primary.generate_answer(query, context, history=history)
                
                if self._is_valid_answer(answer):
                    logger.info(f"llm=gemini latency={round(time.time() - start, 2)}s")
                    return answer
            except Exception as e:
                logger.warning(f"Gemini attempt {attempt+1} failed: {e}")
                time.sleep(1)

        # 🔥 FIX: Pass 'history' instead of 'None'
        try:
            start = time.time()
            answer = self.fallback.generate_answer(query, context, history=history)
            if self._is_valid_answer(answer):
                return answer
        except Exception as e:
            logger.error(f"OpenRouter failed: {e}")

        return "Not found in context"

    def _is_valid_answer(self, answer: str) -> bool:
        if not answer: return False
        
        lowered = answer.lower()
        # Block standard failures
        if "not found in context" in lowered or len(answer.strip()) < 10:
            return False
            
        return True
