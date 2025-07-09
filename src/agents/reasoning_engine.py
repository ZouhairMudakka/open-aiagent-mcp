from __future__ import annotations

from typing import List

import yaml

from ..llm import get_llm_client


class ReasoningEngine:
    def __init__(self):
        # Load model configuration from YAML (fallback to env vars)
        try:
            with open("config/agent_config.yaml", "r", encoding="utf-8") as fp:
                cfg = yaml.safe_load(fp)
            model_cfg = cfg.get("model", {}) if cfg else {}
        except FileNotFoundError:
            model_cfg = {}

        self.llm = get_llm_client(
            provider=model_cfg.get("provider"),
            model=model_cfg.get("name"),
            temperature=model_cfg.get("temperature", 0.7),
        )

    def think(self, goal: str, context: str | None = None) -> str:
        """Generate high-level reasoning steps for a goal."""
        messages: List[dict] = [
            {"role": "system", "content": "You are a helpful reasoning engine that decomposes tasks."},
            {"role": "user", "content": f"Task: {goal}\nContext: {context or ''}\nGive reasoning."},
        ]
        return self.llm.chat(messages, temperature=0.2) 