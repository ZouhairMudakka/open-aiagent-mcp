"""Unified tool specification + dynamic registry.

All agent-facing tools are declared once as `ToolSpec` instances.  The
same object can:  
• produce the OpenAI / Anthropic function-calling schema  
• validate/parse incoming arguments (via Pydantic)  
• execute the underlying handler

Other subsystems (LangGraph agent, docs generator, tests) import the
registry so tools never drift.
"""

from __future__ import annotations

from typing import Callable, Dict, Any, List
from pydantic import BaseModel, create_model, Field

_REGISTRY: Dict[str, "ToolSpec"] = {}


class ToolSpec:
    """A single tool definition.

    Parameters
    ----------
    name: str
        Tool name (unique, snake_case).  This is the function name that
        will appear in the LLM's function list.
    description: str
        A short, user-facing description.
    schema: dict[str, tuple[type, Any]]
        Mapping of argument name → (type, default or Field).
    handler: Callable[[dict], Any]
        Implementation that receives **validated** arguments as a dict
        and returns arbitrary JSON-serialisable result.
    """

    def __init__(
        self,
        *,
        name: str,
        description: str,
        schema: Dict[str, tuple[type, Any]],
        handler: Callable[[Dict[str, Any]], Any],
    ) -> None:
        if name in _REGISTRY:
            raise ValueError(f"Duplicate tool name: {name}")
        self.name = name
        self.description = description
        # Dynamically build Pydantic model for arg validation
        self.ArgsModel: type[BaseModel] = create_model(  # type: ignore[misc]
            f"{name.title()}Args", **{k: (typ, default) for k, (typ, default) in schema.items()}
        )
        self._handler = handler
        _REGISTRY[name] = self

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def validate(self, raw: Dict[str, Any]) -> BaseModel:
        return self.ArgsModel(**raw)

    def run(self, raw_args: Dict[str, Any]):
        validated = self.validate(raw_args)
        return self._handler(validated.dict())

    # ------------------------------------------------------------------
    # LLM function-calling schema
    # ------------------------------------------------------------------

    def openai_schema(self) -> Dict[str, Any]:
        props = {}
        required: List[str] = []
        for field_name, field in self.ArgsModel.model_fields.items():  # type: ignore[attr-defined]
            json_type = _py_to_json_type(field.annotation)
            if json_type == "array":
                props[field_name] = {"type": "array", "items": {"type": "object"}}
            elif json_type == "object":
                props[field_name] = {"type": "object", "additionalProperties": True}
            else:
                props[field_name] = {"type": json_type}
            if field.is_required():
                required.append(field_name)
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required or [],
            },
        }


def _py_to_json_type(py_type: type) -> str:
    mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        dict: "object",
        list: "array",
    }
    return mapping.get(py_type, "string")


# ----------------------------------------------------------------------
# Registry access helpers
# ----------------------------------------------------------------------

def all_tools() -> List[ToolSpec]:
    return list(_REGISTRY.values()) 