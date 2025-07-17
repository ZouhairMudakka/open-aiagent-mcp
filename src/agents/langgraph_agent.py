"""LangGraph-based agent that uses ToolSpec registry + OpenAI function calling."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# Import tool spec modules so they register themselves
from src.agent_tools import postgres_tools  # noqa: F401

from src.agent_tools.spec import all_tools

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Build function schema + tool dispatcher
# -----------------------------------------------------------------------------

TOOLS = all_tools()

# OpenAI tools payload expects {type:"function", function:{...}}
OPENAI_FUNCTIONS = [t.openai_schema() for t in TOOLS]
OPENAI_TOOLS = [{"type": "function", "function": s} for s in OPENAI_FUNCTIONS]

NAME_TO_SPEC = {t.name: t for t in TOOLS}

def _dispatch_tool(tool_call: Dict[str, Any]):
    """Execute the requested tool and return result."""
    import json

    if "name" in tool_call:
        name = tool_call["name"]
        raw_args = tool_call.get("arguments", {})
    elif "function" in tool_call:
        func = tool_call["function"]
        name = func["name"]
        raw_args = func.get("arguments", {})
    else:
        raise ValueError("Malformed tool_call: missing 'name' or 'function.name'")

    # Parse JSON-encoded argument string if necessary
    if isinstance(raw_args, str):
        try:
            args = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError:
            args = {}
    else:
        args = raw_args or {}

    spec = NAME_TO_SPEC.get(name)
    if not spec:
        raise ValueError(f"Unknown tool: {name}")

    return spec.run(args)

# -----------------------------------------------------------------------------
# LangGraph nodes
# -----------------------------------------------------------------------------

llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0,
)

try:
    llm_with_tools = llm.bind_tools(tools=OPENAI_TOOLS)  # LangChain >=0.2.0
except AttributeError:
    # Fallback for older LangChain versions
    llm_with_tools = llm.bind(functions=OPENAI_FUNCTIONS)


# -----------------------------------------------------------------------------
# LangGraph state schema
# -----------------------------------------------------------------------------


class AgentState(TypedDict):
    """Shared state for each LangGraph run."""

    messages: List

# -----------------------------------------------------------------------------
# LangGraph nodes
# -----------------------------------------------------------------------------

async def agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    messages = state["messages"]
    resp = await llm_with_tools.ainvoke(messages)  # type: ignore
    return {"messages": messages + [resp]}

async def tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute either a single OpenAI v1 `function_call` or a list of
    legacy `tool_calls` (OpenAI v2 / Anthropic format)."""

    import json, uuid

    last = state["messages"][-1]

    # New-style single function_call (OpenAI 2023-06 etc.)
    if (fc := last.additional_kwargs.get("function_call")) is not None:
        name = fc["name"]
        args_str: str = fc.get("arguments", "{}")
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
        except json.JSONDecodeError:
            args = {}

        call = {"name": name, "arguments": args, "id": str(uuid.uuid4())}
        tool_calls = [call]
    else:
        # Legacy multi-call format
        tool_calls = last.additional_kwargs.get("tool_calls") or []

    # Preserve existing history then append tool results
    history = state["messages"]
    new_msgs: List[Any] = []
    for call in tool_calls:
        # Derive safe identifiers
        call_id = call.get("id")
        call_name = call.get("name") or call.get("function", {}).get("name", "unknown")

        try:
            result = _dispatch_tool(call)
            new_msgs.append(
                ToolMessage(content=str(result), tool_call_id=call_id or call_name)
            )
        except Exception as exc:
            logger.exception("Tool execution failed: %s", exc)
            new_msgs.append(
                ToolMessage(content=f"ERROR: {exc}", tool_call_id=call_id or call_name)
            )

    return {"messages": history + new_msgs}

# -----------------------------------------------------------------------------
# Build graph
# -----------------------------------------------------------------------------


graph = StateGraph(AgentState)

graph.add_node("agent", agent_node)

graph.add_node("tools", tool_node)

graph.set_entry_point("agent")

def _route(state: AgentState):
    last = state["messages"][-1]
    ak = getattr(last, "additional_kwargs", {})
    if ak.get("function_call") or ak.get("tool_calls"):
        return "tools"
    return "end"          # ← return the label, not END

graph.add_conditional_edges("agent", _route, {"tools": "tools", "end": END})

graph.add_edge("tools", "agent")

workflow = graph.compile()

# -----------------------------------------------------------------------------
# Public Agent wrapper
# -----------------------------------------------------------------------------

class LangGraphAgent:
    def __init__(self):
        self._events: List[Dict[str, Any]] = []

    async def chat(self, prompt: str) -> str:
        initial_state = {"messages": [HumanMessage(content=prompt)]}
        result = await workflow.ainvoke(initial_state)
        final_msg = result["messages"][-1]
        return final_msg.content

    @property
    def events(self):
        return self._events 