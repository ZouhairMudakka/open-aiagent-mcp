from __future__ import annotations

"""Simple heuristics to convert JSON-like Python objects into human-friendly markdown.
Used by WebSocket handler to present tool results clearly without raw JSON."""

from typing import Any, List, Dict
import json, textwrap


def _is_sequence(obj: Any) -> bool:
    return isinstance(obj, (list, tuple))


def _is_mapping(obj: Any) -> bool:
    return isinstance(obj, dict)


def _format_mapping(d: Dict[str, Any]) -> str:
    lines = []
    for k, v in d.items():
        lines.append(f"- **{k}**: {v}")
    return "\n".join(lines)


def _format_sequence(seq: List[Any]) -> str:
    # If list of dicts with consistent keys, render as bullet table
    if seq and all(isinstance(el, dict) for el in seq):
        # normalise key order to first element's keys to avoid ragged tables
        keys = list(seq[0].keys())
        header = " | ".join(keys)
        sep = " | ".join(["---"] * len(keys))
        rows = []
        for el in seq:
            rows.append(" | ".join(str(el.get(k, "")) for k in keys))
        return "\n".join([header, sep, *rows])
    # Generic bullet list
    return "\n".join(f"- {el}" for el in seq)


def pretty_markdown(obj: Any) -> str:
    """Return markdown string if obj is list/dict; otherwise fallback to str(obj)."""
    if _is_mapping(obj):
        return _format_mapping(obj)
    if _is_sequence(obj):
        return _format_sequence(obj)
    return str(obj)


def parse_if_json(text: str):
    """Attempt to parse a string that might be JSON or python-repr dict/list."""
    import ast

    text = text.strip()
    if not text or text[0] not in "[{":
        raise ValueError("not JSON-like")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # fall back to python literal eval (handles single quotes)
        return ast.literal_eval(text) 