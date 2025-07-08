from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class MCPToolCall(BaseModel):
    tool_name: str
    payload: Any


class MCPToolResponse(BaseModel):
    tool_name: str
    result: Any


class MCPMessage(BaseModel):
    role: str  # 'user', 'agent', 'tool', etc.
    content: Any

    class Config:
        arbitrary_types_allowed = True 