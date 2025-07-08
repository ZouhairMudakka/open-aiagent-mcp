from __future__ import annotations

from typing import Dict, List

from .base_agent import Agent
from ..communication.message_bus import MessageBus
from ..communication.agent_communicator import AgentCommunicator


class Coordinator:
    """Creates and manages multiple agents; central registry of tools."""

    def __init__(self):
        self.bus = MessageBus()
        self.agents: Dict[str, Agent] = {}

    def create_agent(self) -> Agent:
        agent = Agent()
        self.agents[agent.id] = agent
        AgentCommunicator(self.bus, agent.id)  # attach communicator if needed later
        return agent

    def broadcast(self, payload):
        for agent_id in self.agents:
            self.bus.publish(f"agent:{agent_id}:in", payload)

    def list_agents(self) -> List[str]:
        return list(self.agents.keys()) 