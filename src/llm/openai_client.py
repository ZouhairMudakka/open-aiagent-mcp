from __future__ import annotations

import os
from typing import List

import requests
import logging

from .base import LLMClient


class OpenAIClient(LLMClient):
    """Tiny wrapper around the OpenAI-compatible Chat Completion endpoint.

    We avoid the heavyweight `openai` SDK to keep the dependency footprint small
    and rely on plain `requests`. The same client can talk to any endpoint that
    speaks the OpenAI REST spec (DeepSeek, OpenRouter, Cursor, etc.) by passing
    a different `base_url` and `api_key`.
    """

    def __init__(
        self,
        api_key: str | None,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.7,
    ):
        super().__init__(model=model, temperature=temperature)
        if not api_key:
            raise RuntimeError("Missing API key for OpenAI-compatible endpoint")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def chat(self, messages: List[dict], temperature: float | None = None) -> str:
        # Per user-provided docs, O-series models handle system prompts
        # differently and have built-in reasoning. We adjust the payload accordingly.
        is_o_series = self.model.startswith(("o1", "o3", "o4"))

        if is_o_series:
            # Remove generic system message for O-series as it can interfere
            # with their specialized reasoning capabilities.
            messages = [m for m in messages if m.get("role") != "system"]

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    def list_models(self) -> List[str]:
        url = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            models = [m["id"] for m in resp.json().get("data", [])]
            if not models:
                # Edge case: user key lacks models.list permission but basic chat works – return o3-mini fallback
                return ["gpt-4.1-mini"]
            return models
        except Exception as exc:
            if hasattr(exc, "response") and exc.response is not None:
                logging.error("OpenAI /models failed %s: %s", exc.response.status_code, exc.response.text)
            else:
                logging.error("OpenAI /models failed: %s", exc)
            return ["o3-mini"] 