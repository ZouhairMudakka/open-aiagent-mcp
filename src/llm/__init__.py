from __future__ import annotations

"""Factory helpers for LLM clients."""

import os
from typing import Any

from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient
from .gemini_client import GeminiClient
from .deepseek_client import DeepSeekClient

__all__ = [
    "get_llm_client",
    "OpenAIClient",
    "AnthropicClient",
    "GeminiClient",
    "DeepSeekClient",
]


def get_llm_client(
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    **kwargs: Any,
):
    """Return an instantiated LLM client for the given provider."""

    provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()

    if provider == "openai":
        model_name = model or os.getenv("OPENAI_MODEL")
        if not model_name:
            raise ValueError("Model name must be specified for OpenAI (set OPENAI_MODEL env or pass via UI).")
        return OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"), model=model_name, temperature=temperature, **kwargs)
    if provider in {"anthropic", "claude"}:
        model_name = model or os.getenv("ANTHROPIC_MODEL")
        if not model_name:
            raise ValueError("Model name must be specified for Anthropic (set ANTHROPIC_MODEL env or choose in UI).")
        return AnthropicClient(api_key=os.getenv("ANTHROPIC_API_KEY"), model=model_name, temperature=temperature)
    if provider in {"gemini", "google"}:
        model_name = model or os.getenv("GEMINI_MODEL")
        if not model_name:
            raise ValueError("Model name must be specified for Gemini (set GEMINI_MODEL env or UI).")
        return GeminiClient(api_key=os.getenv("GOOGLE_API_KEY"), model=model_name, temperature=temperature)
    if provider == "deepseek":
        model_name = model or os.getenv("DEEPSEEK_MODEL")
        if not model_name:
            raise ValueError("Model name must be specified for DeepSeek (set DEEPSEEK_MODEL env or UI).")
        return DeepSeekClient(api_key=os.getenv("DEEPSEEK_API_KEY"), model=model_name, temperature=temperature)

    raise ValueError(f"Unknown LLM provider: {provider}") 