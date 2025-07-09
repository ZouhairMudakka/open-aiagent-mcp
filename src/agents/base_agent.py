from __future__ import annotations

import os
import uuid
from typing import Callable, Dict, Any, List

from pydantic import BaseModel

from ..mcp.protocol import MCPMessage, MCPToolCall, MCPToolResponse  # type: ignore
from ..mcp.connectors.zapier_connector import ZapierConnector  # type: ignore
from ..mcp.connectors.n8n_connector import N8NConnector  # type: ignore
from ..tools.db_tool import DBTool
from ..settings import RuntimeSettings
from ..llm import get_llm_client
import logging
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent, AgentExecutor


class Tool(BaseModel):
    """A simple representation of a callable tool."""

    name: str
    description: str
    func: Callable[[Any], Any]

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class Agent:
    """Minimal agent capable of sending/receiving MCP messages and invoking tools."""

    def __init__(self, settings: RuntimeSettings):
        self.settings_ref = settings
        self.id = str(uuid.uuid4())
        self.tools: Dict[str, Tool] = {}
        self.zapier = ZapierConnector(api_key=os.getenv("ZAPIER_API_KEY"))
        self.n8n = N8NConnector(api_key=os.getenv("N8N_API_KEY"))

        # Holds metadata for the most recent chat call (tool events, etc.)
        self._events: List[Dict[str, Any]] = []

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

        # LangChain agent executor (lazy init)
        self._executor: AgentExecutor | None = None

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

        # Reset per-call event log
        self._events = []

        # Simple pattern: /toolName arg1 arg2
        if prompt.startswith("/"):
            split = prompt[1:].split(" ", 1)
            tool_name = split[0]
            args = split[1] if len(split) > 1 else ""
            return str(self.invoke_tool(tool_name, args))

        # ---------------------------------------------------------------
        # If provider is openai and tools available, use LangChain agent
        # ---------------------------------------------------------------

        settings = self.settings_ref

        if settings.provider == "openai" and settings.model:
            return self._chat_via_langchain(prompt, settings)

        # Fallback: send to LLM
        if not settings.model:
            return "[ERROR] No model selected. Choose one in the settings bar."

        try:
            client = get_llm_client(
                provider=settings.provider,
                model=settings.model,
                temperature=settings.temperature,
            )
            messages = [
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt},
            ]
            reply = client.chat(messages)
            logging.info("[chat] provider=%s model=%s", settings.provider, settings.model)
            return reply
        except Exception as exc:
            logging.error("Chat LLM call failed: %s", exc)
            return f"[ERROR] LLM call failed: {exc}"

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
        logging.debug("[tool] invoking name=%s payload=%s", tool_name, payload)
        print("[DEBUG] tool invoke", tool_name, payload)

        # If the payload is a JSON string (like '{"action":"add"}') convert it to a dict
        if isinstance(payload, str):
            import json
            json_candidate = payload.strip()
            if json_candidate.startswith("{") and json_candidate.endswith("}"):
                try:
                    payload = json.loads(json_candidate)
                except json.JSONDecodeError:
                    # leave as-is; tool may expect plain string
                    pass
        # Local tools have priority
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            result = tool(payload)
            self._events.append({"tool": tool_name, "payload": payload, "result": result})
            logging.debug("[tool] result name=%s result=%s", tool_name, result)
            print("[DEBUG] tool result", tool_name, result)
            return result

        # External connectors
        if tool_name.startswith("zapier:"):
            result = self.zapier.call_tool(tool_name.split(":", 1)[1], payload)
            self._events.append({"tool": tool_name, "payload": payload, "result": result})
            logging.debug("[tool] zapier result name=%s result=%s", tool_name, result)
            return result
        if tool_name.startswith("n8n:"):
            result = self.n8n.call_tool(tool_name.split(":", 1)[1], payload)
            self._events.append({"tool": tool_name, "payload": payload, "result": result})
            logging.debug("[tool] n8n result name=%s result=%s", tool_name, result)
            return result

        raise ValueError(f"Unknown tool: {tool_name}")

    # ------------------------------------------------------------------
    # Event access helpers
    # ------------------------------------------------------------------

    @property
    def events(self) -> List[Dict[str, Any]]:  # noqa: D401
        """Return metadata collected during the last chat call."""
        return self._events

    # ------------------------------------------------------------------
    # LangChain helper
    # ------------------------------------------------------------------

    def _build_executor(self, settings: RuntimeSettings):
        """Create a LangChain AgentExecutor with current tool registry."""
        if self._executor and self._executor.agent.llm.model_name == settings.model:
            return  # already built for same model

        # Convert local tools to StructuredTool
        lc_tools = []
        for t in self.tools.values():
            if not t.description:
                continue
            def _make_callable(f):
                # Ensure we pass a plain dict payload
                def _inner(payload: dict):
                    return f(payload)

                return _inner

            lc_tools.append(
                StructuredTool.from_function(
                    name=t.name,
                    description=t.description,
                    func=_make_callable(t.func),
                )
            )

        llm = ChatOpenAI(model_name=settings.model, temperature=settings.temperature)
        system_prompt = (
            "You are an MCP-aware assistant. If a tool can satisfy the user,"
            " return a JSON function call. Otherwise respond normally."
        )
        self._executor = create_openai_functions_agent(llm, lc_tools, system_prompt)

    def _chat_via_langchain(self, prompt: str, settings: RuntimeSettings) -> str:
        try:
            self._build_executor(settings)
            assert self._executor is not None
            result = self._executor.invoke({"input": prompt})
            # LangChain returns dict
            return result["output"] if isinstance(result, dict) else str(result)
        except Exception as exc:
            logging.error("LangChain agent failed: %s", exc)
            # fallback to basic LLM call
            return self._llm_fallback(prompt, settings)

    def _llm_fallback(self, prompt: str, settings: RuntimeSettings) -> str:
        try:
            client = get_llm_client(
                provider=settings.provider,
                model=settings.model,
                temperature=settings.temperature,
            )
            messages = [
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt},
            ]
            return client.chat(messages)
        except Exception as exc:
            logging.error("LLM fallback failed: %s", exc)
            return f"[ERROR] LLM call failed: {exc}" 