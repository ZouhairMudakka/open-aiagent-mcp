import os
import pytest
from sqlalchemy.exc import OperationalError

# Ensure tests only run when DATABASE_URL points to Postgres
from src.tools.postgres_tool import PostgresDBTool
from src.db.session import engine, SessionLocal

PG_URL = os.getenv("DATABASE_URL", "").lower()

requires_pg = pytest.mark.skipif(
    not PG_URL.startswith("postgres"), reason="Postgres DATABASE_URL required for integration tests"
)

tool = PostgresDBTool()

test_table_payload = {
    "action": "create_table",
    "table": "test_items",
    "columns": [
        {"name": "id", "type": "integer", "pk": True},
        {"name": "name", "type": "text", "nullable": False},
        {"name": "qty", "type": "integer", "nullable": False},
    ],
}

@requires_pg
def test_create_table():
    resp = tool(test_table_payload)
    assert resp["created"] == "test_items"

@requires_pg
def test_insert_and_select():
    tool({"action": "insert", "table": "test_items", "values": {"name": "Widget", "qty": 5}})
    rows = tool({"action": "select", "table": "test_items"})
    assert any(r["name"] == "Widget" for r in rows)

@requires_pg
def test_aggregate_sum():
    # Insert extra rows
    tool({"action": "insert", "table": "test_items", "values": {"name": "Widget", "qty": 3}})
    tool({"action": "insert", "table": "test_items", "values": {"name": "Gadget", "qty": 2}})
    resp = tool({"action": "aggregate", "table": "test_items", "operation": "sum", "column": "qty"})
    assert resp["value"] == 10  # 5 + 3 + 2

@requires_pg
def test_group_by():
    resp = tool({"action": "group_by", "table": "test_items", "column": "name", "top_n": 2})
    assert any(e["value"] == "Widget" and e["count"] >= 2 for e in resp["rows"])

@requires_pg
def test_invalid_aggregate():
    with pytest.raises(ValueError):
        tool({"action": "aggregate", "table": "test_items", "operation": "median", "column": "qty"}) 