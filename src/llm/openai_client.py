from __future__ import annotations

import os
from typing import List

import requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")


class OpenAIClient:
    """Very small wrapper around OpenAI Chat Completion endpoint.

    This avoids pulling in the heavy `openai` SDK, so we rely on `requests`.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY env variable is not set")
        self.model = model or MODEL_NAME

    def chat(self, messages: List[dict], temperature: float = 0.7) -> str:
        url = f"{OPENAI_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip() 