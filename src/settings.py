from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class RuntimeSettings:
    """Mutable runtime config controlled by the web UI."""

    provider: str = "openai"  # default provider only; user can change via UI/env
    model: str | None = None   # determined dynamically from provider list
    temperature: float = 0.7

    def to_dict(self):
        return asdict(self) 