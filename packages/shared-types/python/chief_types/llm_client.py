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
import google.generativeai as genai

logger = logging.getLogger("chief.llm")


class LLMClient:
    """Unified client for OpenAI and Gemini."""

    def __init__(self):
        self._openai_client = None
        self._gemini_initialized = False

    def _get_openai(self) -> AsyncOpenAI:
        if not self._openai_client:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key or api_key == "sk-changeme_openai_key":
                raise ValueError("OPENAI_API_KEY not set or invalid.")
            self._openai_client = AsyncOpenAI(api_key=api_key)
        return self._openai_client

    def _init_gemini(self) -> None:
        if not self._gemini_initialized:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key or api_key == "AIzaSy_changeme_gemini_key":
                raise ValueError("GEMINI_API_KEY not set or invalid.")
            genai.configure(api_key=api_key)
            self._gemini_initialized = True

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
            return await self._call_gemini(model_id, prompt, system_prompt, max_tokens, temperature)
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
            kwargs["response_format"] = {"type": "json_object"}
            
        response = await client.chat.completions.create(**kwargs)
        
        content = response.choices[0].message.content or ""
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        
        return content, prompt_tokens, completion_tokens

    async def _call_gemini(self, model_id: str, prompt: str, system_prompt: str | None, max_tokens: int, temperature: float) -> tuple[str, int, int]:
        self._init_gemini()
        
        # Determine specific model string
        gemini_model_id = "gemini-2.5-pro" if "pro" in model_id.lower() else "gemini-2.5-flash"
        
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        model = genai.GenerativeModel(
            model_name=gemini_model_id,
            system_instruction=system_prompt,
            generation_config=generation_config
        )
        
        response = await model.generate_content_async(prompt)
        
        content = response.text
        
        # Approximate token count for Gemini as exact usage stats aren't always reliably returned in the basic SDK object
        prompt_tokens = model.count_tokens(prompt).total_tokens
        completion_tokens = model.count_tokens(content).total_tokens
        
        return content, prompt_tokens, completion_tokens
