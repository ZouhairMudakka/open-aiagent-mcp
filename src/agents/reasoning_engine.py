from __future__ import annotations

from typing import List

from ..llm.openai_client import OpenAIClient


class ReasoningEngine:
    def __init__(self):
        self.llm = OpenAIClient()

    def think(self, goal: str, context: str | None = None) -> str:
        """Generate high-level reasoning steps for a goal."""
        messages: List[dict] = [
            {"role": "system", "content": "You are a helpful reasoning engine that decomposes tasks."},
            {"role": "user", "content": f"Task: {goal}\nContext: {context or ''}\nGive reasoning."},
        ]
        return self.llm.chat(messages, temperature=0.2) 