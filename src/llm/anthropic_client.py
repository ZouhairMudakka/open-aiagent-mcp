from __future__ import annotations

"""Minimal synchronous Claude client using Anthropic REST API.

We keep the dependency footprint small by using `requests` instead of the
heavy official SDK. This is more than enough for a PoC.
"""

import os
import requests
from typing import List, Dict, Any
import logging

from .base import LLMClient


class AnthropicClient(LLMClient):
    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"  # required header

    def __init__(self, api_key: str | None, model: str, temperature: float = 0.7):
        super().__init__(model=model, temperature=temperature)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing ANTHROPIC_API_KEY env variable or parameter")

    def chat(self, messages: List[Dict[str, Any]], temperature: float | None = None) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": temperature if temperature is not None else self.temperature,
        }
        resp = requests.post(self.API_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # Anthropic returns list of content blocks; join them
        content_blocks = data["content"]
        if isinstance(content_blocks, list):
            return "".join(block.get("text", "") for block in content_blocks).strip()
        return str(content_blocks).strip()

    def list_models(self) -> List[str]:
        # Anthropic API lacks public model-list endpoint; return common set
        logging.error("Anthropic list_models not implemented or failed to fetch")
        return [] 