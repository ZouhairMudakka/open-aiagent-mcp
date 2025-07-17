"""Postgres tool specs registered at import time."""

from __future__ import annotations

from typing import Dict, Any

from src.agent_tools.spec import ToolSpec
from src.tools.postgres_tool import pg_tool

# -----------------------------------------------------------------------------
# list_tables
# -----------------------------------------------------------------------------

def _list_tables_handler(_: Dict[str, Any]):
    return pg_tool({"action": "list_tables"})

ToolSpec(
    name="list_tables",
    description="List all database tables with row counts.",
    schema={},
    handler=_list_tables_handler,
)

# -----------------------------------------------------------------------------
# describe_table
# -----------------------------------------------------------------------------


def _describe_handler(args: Dict[str, Any]):
    return pg_tool({"action": "describe_table", "table": args["table"]})


ToolSpec(
    name="describe_table",
    description="Describe a table's columns, types, and constraints.",
    schema={"table": (str, ...)},
    handler=_describe_handler,
)

# -----------------------------------------------------------------------------
# create_table
# -----------------------------------------------------------------------------


def _create_table_handler(args: Dict[str, Any]):
    payload = {
        "action": "create_table",
        "table": args["table"],
    }
    if args.get("columns"):
        payload["columns"] = args["columns"]
    return pg_tool(payload)


ToolSpec(
    name="create_table",
    description="Create a new table; optional columns list with {name,type,pk,not_null} objects.",
    schema={
        "table": (str, ...),
        "columns": (list, []),
    },
    handler=_create_table_handler,
)

# -----------------------------------------------------------------------------
# add_column
# -----------------------------------------------------------------------------


def _add_column_handler(args: Dict[str, Any]):
    return pg_tool({
        "action": "add_column",
        "table": args["table"],
        "column": args["column"],
        "data_type": args.get("data_type", "text"),
    })


ToolSpec(
    name="add_column",
    description="Add a column to an existing table.",
    schema={
        "table": (str, ...),
        "column": (str, ...),
        "data_type": (str, "text"),
    },
    handler=_add_column_handler,
)

# -----------------------------------------------------------------------------
# drop_table
# -----------------------------------------------------------------------------


def _drop_table_handler(args: Dict[str, Any]):
    return pg_tool({"action": "drop_table", "table": args["table"]})


ToolSpec(
    name="drop_table",
    description="Drop a table if it exists.",
    schema={"table": (str, ...)},
    handler=_drop_table_handler,
)

# -----------------------------------------------------------------------------
# insert
# -----------------------------------------------------------------------------


def _insert_handler(args: Dict[str, Any]):
    return pg_tool({
        "action": "insert",
        "table": args["table"],
        "values": args["values"],
    })


ToolSpec(
    name="insert_rows",
    description="Insert a single row into a table.",
    schema={
        "table": (str, ...),
        "values": (dict, ...),
    },
    handler=_insert_handler,
)

# -----------------------------------------------------------------------------
# select
# -----------------------------------------------------------------------------


def _select_handler(args: Dict[str, Any]):
    return pg_tool({
        "action": "select",
        "table": args["table"],
        "where": args.get("where", {}),
        "columns": args.get("columns"),
        "limit": args.get("limit"),
    })


ToolSpec(
    name="select_rows",
    description="Select rows from a table with optional filters.",
    schema={
        "table": (str, ...),
        "where": (dict, {}),
        "columns": (list, None),
        "limit": (int, None),
    },
    handler=_select_handler,
) 