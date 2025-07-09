from __future__ import annotations

"""Minimal wrapper around Google Gemini Pro via the `google-generativeai` SDK.
If the SDK is not installed, we raise a helpful error message.
"""

import os
from typing import List, Dict, Any
import logging

from .base import LLMClient


class GeminiClient(LLMClient):
    def __init__(self, api_key: str | None, model: str, temperature: float = 0.7):
        super().__init__(model=model, temperature=temperature)
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing GOOGLE_API_KEY env variable or parameter")
        try:
            import google.generativeai as genai  # noqa: WPS433 (dynamic import)
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "google-generativeai package not installed. Add it to requirements.txt"
            ) from exc
        self.genai = genai
        self.genai.configure(api_key=self.api_key)
        self.model_handle = self.genai.GenerativeModel(self.model)

    def chat(self, messages: List[Dict[str, Any]], temperature: float | None = None) -> str:
        # Gemini SDK wants a single concatenated prompt, but we can emulate
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"[{role.upper()}]: {content}")
        prompt = "\n".join(prompt_parts)
        response = self.model_handle.generate_content(
            prompt,
            generation_config={
                "temperature": temperature if temperature is not None else self.temperature,
            },
        )
        return response.text.strip()

    def list_models(self) -> List[str]:
        try:
            models = self.genai.list_models()
            return [m.name for m in models if "generateContent" in getattr(m, "supported_generation_methods", [])]
        except Exception as exc:
            logging.error("Gemini list_models failed: %s", exc)
            return [] 