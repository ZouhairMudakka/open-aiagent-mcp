from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, List, Any


class MessageBus:
    """Very lightweight pub-sub message bus (process-wide)."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, topic: str, cb: Callable[[Any], None]):
        self._subscribers[topic].append(cb)

    def publish(self, topic: str, payload: Any):
        for cb in list(self._subscribers.get(topic, [])):
            cb(payload) 