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

_EXAMPLE_TOOLS = [
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
        "name": "db_schema",
        "description": "Describe an existing table's structure",
        "params": {"action": "describe_table", "table": "string"},
    },
    {
        "name": "db_schema",
        "description": "List all tables with row counts",
        "params": {"action": "list_tables"},
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

    messages = build_prompt(prompt, _EXAMPLE_TOOLS)
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