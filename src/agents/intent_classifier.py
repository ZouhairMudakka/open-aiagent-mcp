from __future__ import annotations

"""Very lightweight LLM-based intent classifier that maps natural-language
prompts to a tool name + JSON args dict.

Currently supports only OpenAI models (function-calling not needed). If the
LLM returns tool="none" we treat as no-op.
"""

from typing import Any, Dict, Tuple, Optional, List
import json
import logging

from ..llm import OpenAIClient

_SYSTEM_PROMPT = (
    "You are an intent classifier. Return ONLY valid JSON with keys 'tool' and "
    "'args'. If no tool applies, use {'tool': 'none', 'args': {}}."
)

# ---------------------------------------------------------------------------
# Dynamic tool discovery – fallback to static examples when registry empty
# ---------------------------------------------------------------------------


def _collect_tool_examples():
    """Return a list of tool example dicts {name, description, params} sourced from
    `agent_tools.spec` registry. Falls back to the legacy hard-coded list when the
    registry is empty or import fails (keeps unit tests simple).
    """
    try:
        from src.agent_tools.spec import all_tools  # local import to avoid heavy deps at import time

        examples = []
        for spec in all_tools():
            fields = getattr(spec, "ArgsModel").model_fields  # type: ignore[attr-defined]
            examples.append(
                {
                    "name": spec.name,
                    "description": spec.description,
                    "params": {k: _py_to_str(v.annotation) for k, v in fields.items()},
                }
            )
        if examples:
            return examples
    except Exception:
        # Silently fall back – dynamic discovery is best-effort only
        pass
    return _LEGACY_EXAMPLES


# Helper for converting python type to short string (str,int etc.)
def _py_to_str(t):
    mapping = {str: "string", int: "integer", float: "number", bool: "boolean"}
    return mapping.get(t, "string")


# ---------------------------------------------------------------------------
# Legacy static examples (used as fallback)
# ---------------------------------------------------------------------------

_LEGACY_EXAMPLES = [
    {
        "name": "db_add",
        "description": "Add a text entry to the DB",
        "params": {"data": "string"},
    },
    {
        "name": "db_list",
        "description": "List all DB rows",
        "params": {},
    },
    {
        "name": "db_schema",
        "description": "Create or modify tables/columns in Postgres",
        "params": {
            "action": "string",
            "table": "string",
        },
    },
    {
        "name": "db_query",
        "description": "Insert/select/update/delete rows in Postgres",
        "params": {
            "action": "string",
            "table": "string",
        },
    },
    {
        "name": "db_query",
        "description": "List all rows in a table (simple SELECT *).",
        "params": {
            "action": "select",
            "table": "string"
        },
    },
    {
        "name": "db_schema",
        "description": "Describe a table's structure (columns, types).",
        "params": {"action": "describe_table", "table": "string"},
    },
    {
        "name": "db_query",
        "description": "Compute aggregate (avg, sum, min, max, count) on a column.",
        "params": {"action": "aggregate", "table": "string", "operation": "string", "column": "string"},
    },
    {
        "name": "db_query",
        "description": "Compute total quantity of items (sum qty).",
        "params": {"action": "aggregate", "table": "test_items", "operation": "sum", "column": "qty"},
    },
    {
        "name": "db_query",
        "description": "Return top-N item names with counts.",
        "params": {"action": "group_by", "table": "test_items", "column": "name", "top_n": 2},
    },
    {
        "name": "db_query",
        "description": "Return top-N values grouped by a column with counts/percentages.",
        "params": {"action": "group_by", "table": "string", "column": "string", "top_n": "integer"},
    },
    {
        "name": "db_query",
        "description": "Generate a time-series histogram (date_trunc) for a timestamp column.",
        "params": {"action": "time_series", "table": "string", "column": "string", "granularity": "string"},
    },
    {
        "name": "db_query",
        "description": "Insert a new row into a table with explicit values.",
        "params": {"action": "insert", "table": "string", "values": {"any": "object"}},
    },
    {
        "name": "db_query",
        "description": "Select rows using a simple two-table join.",
        "params": {
            "action": "join_select",
            "left_table": "string",
            "right_table": "string",
            "left_key": "string",
            "right_key": "string"
        },
    },
    {
        "name": "send_email",
        "description": "Send an e-mail via Zapier",
        "params": {"to": "string", "subject": "string", "body": "string"},
    },
]


def build_prompt(prompt: str, tools: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    tool_desc = "\n".join(
        f"- {t['name']}: {t['description']} params={list(t['params'].keys())}" for t in tools
    )
    user_msg = (
        f"TOOLS AVAILABLE:\n{tool_desc}\n\n"
        "User message: " + prompt + "\n"  # noqa: RUF001
        "Respond with JSON only."
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]


def classify(prompt: str, openai_api_key: str | None = None) -> Tuple[Optional[str], Dict[str, Any]]:
    """Return (tool_name, args) or (None, {}). Automatically resolves the API key from the
    OPENAI_API_KEY environment variable when not supplied explicitly so that calling code
    doesn't need to pass it around."""

    # Lazily resolve API key from env so the caller doesn't have to thread it through.
    if openai_api_key is None:
        import os

        openai_api_key = os.getenv("OPENAI_API_KEY")

    client = OpenAIClient(api_key=openai_api_key, model="gpt-3.5-turbo", temperature=0)

    examples = _collect_tool_examples()
    messages = build_prompt(prompt, examples)
    try:
        response = client.chat(messages)
        obj = json.loads(response)
        tool = obj.get("tool")
        args = obj.get("args", {})
        if tool == "none":
            return None, {}
        return tool, args if isinstance(args, dict) else {}
    except Exception as exc:
        logging.debug("Intent classifier fallback: %s", exc)
        return None, {} 