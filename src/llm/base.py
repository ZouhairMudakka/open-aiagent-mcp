from __future__ import annotations

"""Common interface for all LLM provider adapters.

Each concrete client should implement a synchronous `chat` method that
accepts a list of messages (OpenAI-style: {"role": "user"|"assistant"|"system", "content": str})
and returns a string response.

This very small abstraction keeps the rest of the codebase provider-agnostic.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class LLMClient(ABC):
    """Abstract base class for language model clients."""

    def __init__(self, model: str, temperature: float = 0.7):
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def chat(self, messages: List[Dict[str, Any]], temperature: float | None = None) -> str:  # noqa: D401, E501
        """Send a chat completion request and return the model reply as text."""
        ...

    def list_models(self) -> List[str]:  # noqa: D401
        """Return list of available model names (best effort)."""
        raise NotImplementedError 