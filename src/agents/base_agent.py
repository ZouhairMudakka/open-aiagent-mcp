from __future__ import annotations

import os
import uuid
from typing import Callable, Dict, Any, List

from pydantic import BaseModel

from ..mcp.protocol import MCPMessage, MCPToolCall, MCPToolResponse  # type: ignore
from ..mcp.connectors.zapier_connector import ZapierConnector  # type: ignore
from ..mcp.connectors.n8n_connector import N8NConnector  # type: ignore
from ..tools.db_tool import DBTool


class Tool(BaseModel):
    """A simple representation of a callable tool."""

    name: str
    description: str
    func: Callable[[Any], Any]

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class Agent:
    """Minimal agent capable of sending/receiving MCP messages and invoking tools."""

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.tools: Dict[str, Tool] = {}
        self.zapier = ZapierConnector(api_key=os.getenv("ZAPIER_API_KEY"))
        self.n8n = N8NConnector(api_key=os.getenv("N8N_API_KEY"))

        # Built-in example tool
        self.register_tool(
            "echo",
            "Returns whatever input it receives.",
            lambda text: text,
        )

        # Database tool (usage: /db {"action": "add", "data": "hello"})
        self.db_tool = DBTool()
        self.register_tool(
            "db",
            "Add, delete, update, or list rows in the sample SQLite DB.",
            self.db_tool,
        )

    # ---------------------------------------------------------------------
    # Tool Registry
    # ---------------------------------------------------------------------
    def register_tool(self, name: str, description: str, func: Callable[[Any], Any]):
        self.tools[name] = Tool(name=name, description=description, func=func)

    # ---------------------------------------------------------------------
    # Chat Interface (very simplified)
    # ---------------------------------------------------------------------
    def chat(self, prompt: str) -> str:
        """Entry point for user to interact with the agent.

        In a production system this would call an LLM; here we route to tools
        if the prompt starts with a special pattern, otherwise we echo.
        """

        # Simple pattern: /toolName arg1 arg2
        if prompt.startswith("/"):
            split = prompt[1:].split(" ", 1)
            tool_name = split[0]
            args = split[1] if len(split) > 1 else ""
            return str(self.invoke_tool(tool_name, args))

        # Default behaviour: return echo
        return f"Agent {self.id} received: {prompt}"

    # ------------------------------------------------------------------
    # MCP Interaction
    # ------------------------------------------------------------------
    def handle_mcp_message(self, message: MCPMessage) -> MCPMessage:
        """Very lightweight MCP message handler."""
        if isinstance(message.content, MCPToolCall):
            tool_name = message.content.tool_name
            payload = message.content.payload
            result = self.invoke_tool(tool_name, payload)
            return MCPMessage(
                role="tool",
                content=MCPToolResponse(tool_name=tool_name, result=result),
            )
        # For non-tool messages, simply echo
        return MCPMessage(role="agent", content=f"Echo: {message.content}")

    # ------------------------------------------------------------------
    # Tool Invocation Logic
    # ------------------------------------------------------------------
    def invoke_tool(self, tool_name: str, payload: Any):
        # Local tools have priority
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            return tool(payload)

        # External connectors
        if tool_name.startswith("zapier:"):
            return self.zapier.call_tool(tool_name.split(":", 1)[1], payload)
        if tool_name.startswith("n8n:"):
            return self.n8n.call_tool(tool_name.split(":", 1)[1], payload)

        raise ValueError(f"Unknown tool: {tool_name}") 