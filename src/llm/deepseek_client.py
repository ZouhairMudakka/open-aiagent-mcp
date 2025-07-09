from __future__ import annotations

"""DeepSeek client – reuses the OpenAI-compatible chat completion format."""

import os
import logging
from typing import List

from .openai_client import OpenAIClient


class DeepSeekClient(OpenAIClient):
    def __init__(self, api_key: str | None = None, model: str | None = None, temperature: float = 0.7):
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if model is None:
            model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        super().__init__(api_key=api_key, model=model, base_url=base_url, temperature=temperature)

    def list_models(self) -> List[str]:
        # DeepSeek exposes /models like OpenAI
        try:
            import requests

            headers = {"Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY', '')}"}
            resp = requests.get(f"{os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')}/models", headers=headers, timeout=10)
            resp.raise_for_status()
            return [m["id"] for m in resp.json().get("data", [])]
        except Exception as exc:
            logging.error("DeepSeek list_models failed: %s", exc)
            return [] 