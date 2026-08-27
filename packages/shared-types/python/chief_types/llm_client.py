"""
Chief AI Startup OS — LLM Client Wrapper
Implements: AIDD §4 (Multi-model routing)

Provides a unified interface for calling Google Gemini and OpenAI models.
Requires `google-genai` and `openai` Python packages.
"""

import os
import logging
import time
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger("chief.llm")


class LLMClient:
    """Unified client for OpenAI and Gemini."""

    def __init__(self):
        self._openai_client = None
        self._gemini_client = None

    def _get_openai(self) -> AsyncOpenAI:
        if not self._openai_client:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key or api_key == "sk-changeme_openai_key":
                raise ValueError("OPENAI_API_KEY not set or invalid.")
            self._openai_client = AsyncOpenAI(api_key=api_key)
        return self._openai_client

    def _get_gemini(self) -> Any:
        if not self._gemini_client:
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key or api_key == "AIzaSy_changeme_gemini_key":
                raise ValueError("GEMINI_API_KEY not set or invalid.")
            self._gemini_client = genai.Client(api_key=api_key)
        return self._gemini_client

    async def generate(
        self,
        provider: str,
        model_id: str,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        response_format: Any = None,
    ) -> tuple[str, int, int]:
        """
        Execute an LLM generation call.
        Returns: (content_string, prompt_tokens, completion_tokens)
        """
        if provider == "openai":
            return await self._call_openai(model_id, prompt, system_prompt, max_tokens, temperature, response_format)
        elif provider == "google":
            return await self._call_gemini(model_id, prompt, system_prompt, max_tokens, temperature, response_format)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    async def _call_openai(self, model_id: str, prompt: str, system_prompt: str | None, max_tokens: int, temperature: float, response_format: Any) -> tuple[str, int, int]:
        client = self._get_openai()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        kwargs = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format:
            # We assume response_format is a Pydantic model for structured output
            # If it's a Pydantic model, OpenAI supports it via response_format={"type": "json_schema", "json_schema": ...}
            # For simplicity, if it's passed, we request generic json_object (unless we implement strict schema extraction).
            kwargs["response_format"] = {"type": "json_object"}
            
        response = await client.chat.completions.create(**kwargs)
        
        content = response.choices[0].message.content or ""
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        
        # Strip markdown json block just in case
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
        
        logger.info(f"[LLM_CALL_SITE] Provider=openai Model={model_id}\n=== System Prompt ===\n{system_prompt}\n=== Injected Prompt ===\n{prompt}\n=== Raw Response ===\n{content}\n====================")
        
        return content, prompt_tokens, completion_tokens

    async def _call_gemini(self, model_id: str, prompt: str, system_prompt: str | None, max_tokens: int, temperature: float, response_format: Any) -> tuple[str, int, int]:
        from google.genai import types
        
        client = self._get_gemini()
        
        gemini_model_id = "gemini-2.5-flash"
        
        config_kwargs = {
            "temperature": temperature,
            "max_output_tokens": max(max_tokens, 8192),
        }
        
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
            
        if response_format:
            config_kwargs["response_mime_type"] = "application/json"
            # If response_format is a Pydantic model, pass it directly
            if hasattr(response_format, 'model_json_schema'):
                config_kwargs["response_schema"] = response_format
        
        config = types.GenerateContentConfig(**config_kwargs)
        
        # google-genai AsyncClient uses aiosession internally if you call aio methods
        response = await client.aio.models.generate_content(
            model=gemini_model_id,
            contents=prompt,
            config=config
        )
        
        content = response.text
        
        # Approximate token count since we don't always get it back cleanly in standard text requests
        try:
            prompt_resp = await client.aio.models.count_tokens(model=gemini_model_id, contents=prompt)
            prompt_tokens = prompt_resp.total_tokens
            comp_resp = await client.aio.models.count_tokens(model=gemini_model_id, contents=content)
            completion_tokens = comp_resp.total_tokens
        except Exception:
            prompt_tokens = 0
            completion_tokens = 0
            
        # Strip markdown json block just in case
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
        
        logger.info(f"[LLM_CALL_SITE] Provider=google Model={gemini_model_id}\n=== System Prompt ===\n{system_prompt}\n=== Injected Prompt ===\n{prompt}\n=== Raw Response ===\n{content}\n====================")
        
        return content, prompt_tokens, completion_tokens
