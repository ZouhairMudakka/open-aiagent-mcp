from __future__ import annotations

from typing import Any, Callable

from .message_bus import MessageBus


class AgentCommunicator:
    def __init__(self, bus: MessageBus, agent_id: str):
        self.bus = bus
        self.agent_id = agent_id
        self.topic_in = f"agent:{agent_id}:in"
        self.topic_out = f"agent:{agent_id}:out"

    def send(self, target_agent_id: str, payload: Any):
        self.bus.publish(f"agent:{target_agent_id}:in", payload)

    def on_message(self, cb: Callable[[Any], None]):
        self.bus.subscribe(self.topic_in, cb) 