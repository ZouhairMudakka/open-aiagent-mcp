from __future__ import annotations

from typing import List

from .reasoning_engine import ReasoningEngine


class Planner:
    def __init__(self):
        self.engine = ReasoningEngine()

    def plan(self, goal: str) -> List[str]:
        reasoning = self.engine.think(goal)
        # naive split by newline/bullet for now
        steps = [line.strip("- •\t ") for line in reasoning.split("\n") if line.strip()]
        return steps or [reasoning] 