from typing import List, Dict
import time

from core.ai.llm.base import BaseLLM
from shared.logging import get_logger

from infra.ai.llm.gemini_client import GeminiClient
from infra.ai.llm.openrouter_client import OpenRouterClient
from infra.observability.langfuse_client import langfuse

logger = get_logger(__name__)


class GatewayLLM(BaseLLM):

    def __init__(self):
        self.primary = GeminiClient()
        self.fallback = OpenRouterClient()

    
    async def generate_answer(self, query: str, context: str, history: List[Dict]) -> str:
    
        with langfuse.start_as_current_observation(
            name="chat_gen_static",
            input={"query": query}
        ) as trace:

            prompt = self._build_prompt(query, context, history)

            # Primary Attempt
            try:
                with langfuse.start_as_current_observation(
                    name="gemini_call",
                    as_type="generation",
                    model="gemini-pro",
                    input=prompt
                ) as gen:

                    answer = await self.primary.generate(prompt)

                    if self._valid(answer):
                        gen.update(output=answer)
                        trace.update(output=answer)
                        langfuse.flush()
                        return answer

                    gen.update(output=answer, metadata={"validation": "failed"})

            except Exception as e:
                logger.warning(f"Gemini failed: {e}")
                trace.update(metadata={"primary_error": str(e)})

            # Fallback Attempt
            try:
                with langfuse.start_as_current_observation(
                    name="fallback_call",
                    as_type="generation",
                    model="openrouter",
                    input=prompt
                ) as fb_gen:

                    answer = await self.fallback.generate(prompt)
                    final = answer if answer else "Not found in context"

                    fb_gen.update(output=final)
                    trace.update(output=final)

                    langfuse.flush()
                    return final

            except Exception as e:
                logger.error(f"Total failure: {e}")
                trace.update(status_message="failed", metadata={"error": str(e)})
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
    #         if primary_span:
    #             primary_span.update(metadata={"error_type": "primary_failure", "error_msg": str(e)})
    #             primary_span.end(status_message="failed")

    #     # Fallback (OpenRouter)
    #     try:
    #         fallback_span = trace.span(name="llm_fallback_call")
    #         fallback_output = ""
    #         for chunk in self.fallback.stream(prompt):
    #             fallback_output += chunk
    #             full_output += chunk
    #             yield chunk
            
    #         if fallback_output:
    #             fallback_span.end(output=fallback_output, status_message="fallback_success")
    #         else:
    #             fallback_span.end(output="[No output]", status_message="fallback_no_output")
                
    #     except Exception as e:
    #         logger.error(f"Fallback stream failed: {e}")
            
    #         if primary_span:
    #             trace.update(status_message="Total Failure", metadata={"error": str(e)})
    #         yield "[ERROR: AI service unavailable]"
    
    def stream_answer(self, query: str, context: str, history):

        with langfuse.start_as_current_observation(
            name="chat_request",
            input={"query": query, "history_count": len(history)}
        ) as trace:

            prompt = self._build_prompt(query, context, history)

            full_output = ""

            # Primary (Gemini)
            try:
                with langfuse.start_as_current_observation(
                    name="llm_streaming_call",
                    as_type="generation",
                    model="gemini-pro",
                    input=prompt
                ) as primary_span:

                    for chunk in self.primary.stream(prompt):
                        full_output += chunk
                        yield chunk

                    if full_output:
                        primary_span.update(output=full_output)
                        trace.update(output=full_output)   # ✅ IMPORTANT

            except Exception as e:
                logger.warning(f"Gemini stream failed: {e}")
                trace.update(metadata={"primary_error": str(e)})

            # Fallback
            try:
                with langfuse.start_as_current_observation(
                    name="llm_fallback_call",
                    as_type="generation",
                    model="openrouter",
                    input=prompt
                ) as fallback_span:

                    fallback_output = ""

                    for chunk in self.fallback.stream(prompt):
                        fallback_output += chunk
                        full_output += chunk
                        yield chunk

                    final = fallback_output if fallback_output else "[No output]"

                    fallback_span.update(output=final)
                    trace.update(output=full_output if full_output else final)

            except Exception as e:
                logger.error(f"Fallback stream failed: {e}")
                trace.update(status_message="failed", metadata={"error": str(e)})
                yield "[ERROR: AI service unavailable]"

            langfuse.flush()   