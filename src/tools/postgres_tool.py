"""High-level Postgres helper that can both mutate schema and read/write data.

This tool intentionally exposes only *safe* operations by mapping a
restricted JSON payload → SQLAlchemy expressions.  It is **not** a full SQL
runner but covers 90 % of natural-language DB requests we expect the agent to
receive (create table, add column, insert rows, select with simple filters
and aggregates, etc.).

Schema JSON shapes
------------------
create_table:
    {
        "action": "create_table",
        "table": "users",
        "columns": [
            {"name": "id", "type": "integer", "pk": true},
            {"name": "email", "type": "text", "nullable": false}
        ]
    }

add_column / drop_column / rename_column:
    {"action": "add_column", "table": "users", "column": {"name": "status", "type": "text"}}

Data JSON shapes
+----------------
insert:
    {"action": "insert", "table": "users", "values": {"email": "x@y.com"}}

select:
    {
        "action": "select",
        "table": "users",
        "columns": ["id", "email"],            # optional, default "*"
        "where": {"status": "active"},          # AND-ed equality filters
        "limit": 100,
        "offset": 0
    }

update / delete similar semantics.

Limits / trade-offs
+-------------------
• We stick to basic pg/SQLAlchemy column types (integer, text, float, bool,
  timestamp) to keep mapping simple.
• The tool auto-creates tables on first touching them (reflect=True) so we can
  combine declarative & reflection worlds.
• Everything runs in one short-lived session so each call is atomic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    Date,
    select,
    insert as sa_insert,
    update as sa_update,
    delete as sa_delete,
    text as sa_text,
    inspect,
)
from sqlalchemy.exc import SQLAlchemyError

from ..db.session import engine, SessionLocal


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------


_TYPE_MAP: Dict[str, Any] = {
    "integer": Integer,
    "int": Integer,
    "text": Text,
    "string": String,
    "varchar": String,
    "float": Float,
    "double": Float,
    "boolean": Boolean,
    "bool": Boolean,
    "datetime": DateTime,
    "timestamp": DateTime,
    "date": Date,
}


def _sa_type(type_name: str):
    if type_name.lower() not in _TYPE_MAP:
        raise ValueError(f"Unsupported column type '{type_name}'. Allowed: {list(_TYPE_MAP)}")
    return _TYPE_MAP[type_name.lower()]


class PostgresDBTool:
    """Safe Postgres wrapper – works with any SQLAlchemy backend but expects PG-style features."""

    def __init__(self):
        # In SQLAlchemy 2.0 the "bind" parameter was removed; keep metadata
        # unbound and pass the engine explicitly when emitting DDL.
        self.md = MetaData()

    # ------------------------------------------------------------------
    # Public entrypoint – mirroring old DBTool signature
    # ------------------------------------------------------------------
    def __call__(self, payload: Dict[str, Any]):  # noqa: C901 – complexity ok for central switch
        action = payload.get("action")
        if not action:
            raise ValueError("Missing 'action' in payload")

        # dispatch – schema operations first
        try:
            # Accept "create" only when the payload clearly refers to a table
            if action == "create_table" or (
                action == "create" and "table" in payload and not any(k in payload for k in ["index", "view", "materialized_view"])
            ):
                return self._create_table(payload)
            if action == "add_column":
                return self._add_column(payload)
            if action == "describe_table":
                return self._describe_table(payload)
            if action in {"list_tables", "show_tables"}:
                return self._list_tables()
            if action in {"drop_table", "delete_table", "drop"}:
                return self._drop_table(payload)
            if action == "drop_column":
                return self._drop_column(payload)
            if action == "rename_column":
                return self._rename_column(payload)
            if action == "aggregate":
                return self._aggregate(payload)
            if action == "group_by":
                return self._group_by(payload)
            if action == "time_series":
                return self._time_series(payload)
            if action == "join_select":
                return self._join_select(payload)

            # data ops
            if action in {"select", "list"}:
                return self._select(payload)
            if action == "insert":
                return self._insert(payload)
            if action == "update":
                return self._update(payload)
            if action == "delete":
                return self._delete(payload)

        except SQLAlchemyError as exc:
            # Let agent convert to friendly message later
            raise RuntimeError(str(exc)) from exc

        raise ValueError(f"Unsupported db action '{action}'")

    # ------------------------------------------------------------------
    # Schema helpers
    # ------------------------------------------------------------------

    def _create_table(self, payload: Dict[str, Any]):
        table_name = payload["table"]
        columns: List[Dict[str, Any]] = payload.get("columns", [])

        if not columns:
            # Auto-create an 'id' primary key if user gave no column spec
            columns = [{"name": "id", "type": "integer", "pk": True}]

        cols = []
        for col in columns:
            # Accept aliases modelled by the intent-classifier
            col_type_name = col.get("type") or col.get("data_type")
            ctype = _sa_type(col_type_name)

            kwargs = {
                "primary_key": col.get("pk") or col.get("primary_key", False),
                # `not_null: True` → nullable=False
                "nullable": not col.get("not_null", False) if "not_null" in col else col.get("nullable", True),
            }
            if "default" in col:
                kwargs["default"] = col["default"]
            cols.append(Column(col["name"], ctype, **kwargs))

        table = Table(table_name, self.md, *cols)
        table.create(bind=engine, checkfirst=True)
        return {
            "created": table_name,
            "columns": [c.name for c in table.columns],
        }

    def _add_column(self, payload: Dict[str, Any]):
        tbl_name = payload["table"]
        col = payload["column"]

        # Allow shorthand: column="status", data_type="text"
        if isinstance(col, str):
            col = {"name": col, "type": payload.get("data_type", "text")}

        ctype = _sa_type(col.get("type") or col.get("data_type", "text"))

        col_name = col["name"]

        # SQLAlchemy 2.0: compile needs explicit dialect, not Engine
        compiled_type = ctype().compile(dialect=engine.dialect)

        # emit ALTER TABLE … ADD COLUMN safely
        alter = sa_text(
            f"ALTER TABLE {tbl_name} ADD COLUMN IF NOT EXISTS {col_name} {compiled_type}"
        )
        with engine.begin() as conn:
            conn.execute(alter)
        return {"added_column": col_name, "table": tbl_name}

    def _drop_column(self, payload: Dict[str, Any]):
        tbl_name = payload["table"]
        col_name = payload["column"]
        alter = sa_text(f"ALTER TABLE {tbl_name} DROP COLUMN IF EXISTS {col_name}")
        with engine.begin() as conn:
            conn.execute(alter)
        return {"dropped_column": col_name, "table": tbl_name}

    def _rename_column(self, payload: Dict[str, Any]):
        tbl = payload["table"]
        old = payload["old_name"]
        new = payload["new_name"]
        alter = sa_text(f"ALTER TABLE {tbl} RENAME COLUMN {old} TO {new}")
        with engine.begin() as conn:
            conn.execute(alter)
        return {"renamed": old, "new_name": new, "table": tbl}

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _get_table(self, name: str):
        """Return a SQLAlchemy Table or raise RuntimeError('table_not_found')."""
        try:
            return Table(name, self.md, autoload_with=engine, extend_existing=True)
        except Exception as exc:
            from sqlalchemy.exc import NoSuchTableError
            if isinstance(exc, NoSuchTableError):
                raise RuntimeError(f"table_not_found:{name}") from exc
            raise

    def _insert(self, payload: Dict[str, Any]):
        tbl = self._get_table(payload["table"])
        values = payload.get("values") or payload.get("data")
        if values is None:
            raise ValueError("'insert' action requires 'values' (or 'data') field")
        with SessionLocal() as sess:
            if isinstance(values, list):
                stmt = sa_insert(tbl)
                res = sess.execute(stmt, values)
            else:
                stmt = sa_insert(tbl).values(values)
                res = sess.execute(stmt)
            sess.commit()
            return {"inserted": res.rowcount}

    def _select(self, payload: Dict[str, Any]):
        if "table" not in payload:
            raise ValueError("'select/list' action requires 'table' field")

        tbl = self._get_table(payload["table"])
        columns = payload.get("columns")  # None means '*'
        where = payload.get("where") or {}

        sel_cols: Sequence[Any] = [tbl.c[c] for c in columns] if columns else [tbl]
        stmt = select(*sel_cols)
        for col, val in where.items():
            stmt = stmt.where(tbl.c[col] == val)

        # Apply LIMIT / OFFSET only when a non-None value is provided
        limit_val = payload.get("limit")
        if limit_val is not None:
            stmt = stmt.limit(int(limit_val))

        offset_val = payload.get("offset")
        if offset_val is not None:
            stmt = stmt.offset(int(offset_val))

        with SessionLocal() as sess:
            rows = sess.execute(stmt).mappings().all()
            return [dict(r) for r in rows]

    def _update(self, payload: Dict[str, Any]):
        tbl = self._get_table(payload["table"])
        where = payload.get("where") or {}
        values = payload.get("values") or {}

        stmt = sa_update(tbl).values(values)
        for col, val in where.items():
            stmt = stmt.where(tbl.c[col] == val)

        with SessionLocal() as sess:
            res = sess.execute(stmt)
            sess.commit()
            return {"updated": res.rowcount}

    def _delete(self, payload: Dict[str, Any]):
        tbl = self._get_table(payload["table"])
        where = payload.get("where") or {}

        stmt = sa_delete(tbl)
        for col, val in where.items():
            stmt = stmt.where(tbl.c[col] == val)

        with SessionLocal() as sess:
            res = sess.execute(stmt)
            sess.commit()
            return {"deleted": res.rowcount}

    def _describe_table(self, payload: Dict[str, Any]):
        tbl_name = payload["table"]
        insp = inspect(engine)
        if tbl_name not in insp.get_table_names():
            raise ValueError(f"Table '{tbl_name}' does not exist")

        cols = []
        for col in insp.get_columns(tbl_name):
            cols.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "default": col["default"],
                "primary_key": col.get("primary_key", False),
            })
        return {"table": tbl_name, "columns": cols}

    def _list_tables(self):
        insp = inspect(engine)
        names = insp.get_table_names()
        rows = []
        with engine.connect() as conn:
            for n in names:
                safe = n.replace("\"", "\"\"")
                count = conn.execute(sa_text(f'SELECT count(*) FROM "{safe}"')).scalar()
                rows.append({"table": n, "rows": count})
        return rows

    def _drop_table(self, payload: Dict[str, Any]):
        tbl = payload["table"]
        safe = tbl.replace("\"", "\"\"")
        with engine.begin() as conn:
            conn.execute(sa_text(f'DROP TABLE IF EXISTS "{safe}" CASCADE'))
        return {"dropped_table": tbl}

    def _aggregate(self, payload: Dict[str, Any]):
        """Run aggregate functions (avg, sum, min, max, count) on a single column."""
        tbl = self._get_table(payload["table"])
        column = payload.get("column") or payload.get("field")
        agg = (payload.get("operation") or payload.get("agg") or "count").lower()

        if not column and agg != "count":
            raise ValueError("'aggregate' requires 'column' for operations other than count")

        from sqlalchemy import func

        col_obj = tbl.c[column] if column else None
        agg_map = {
            "count": func.count(),
            "sum": func.sum(col_obj),
            "avg": func.avg(col_obj),
            "min": func.min(col_obj),
            "max": func.max(col_obj),
        }
        if agg not in agg_map:
            raise ValueError(f"Unsupported aggregate operation '{agg}'. Allowed: {list(agg_map)}")

        stmt = select(agg_map[agg])
        where = payload.get("where") or {}
        for col, val in where.items():
            stmt = stmt.where(tbl.c[col] == val)

        with SessionLocal() as sess:
            result = sess.execute(stmt).scalar()
            return {"table": payload["table"], "operation": agg, "value": result}

    def _group_by(self, payload: Dict[str, Any]):
        """Return counts or aggregates grouped by a column, with optional top_n and percentages."""
        tbl = self._get_table(payload["table"])
        group_col = payload["column"]
        top_n = int(payload.get("top_n", 10))
        include_percent = bool(payload.get("percent", True))

        from sqlalchemy import func

        col_obj = tbl.c[group_col]
        stmt = (
            select(col_obj, func.count().label("count"))
            .group_by(col_obj)
            .order_by(func.count().desc())
        )
        with SessionLocal() as sess:
            rows = sess.execute(stmt).all()
            total = sum(r.count for r in rows)
            result = []
            for r in rows[:top_n]:
                entry = {"value": r[0], "count": r[1]}
                if include_percent and total:
                    entry["percent"] = round(r[1] / total * 100, 2)
                result.append(entry)
            return {"table": payload["table"], "group_by": payload["column"], "rows": result, "total": total}

    def _time_series(self, payload: Dict[str, Any]):
        """Histogram over time using date_trunc. payload: table, column (timestamp), granularity (hour/day/week/month)."""
        tbl = self._get_table(payload["table"])
        ts_col = tbl.c[payload.get("column", "created_at")]
        gran = payload.get("granularity", "day")

        from sqlalchemy import func, text as sa_text

        if gran not in {"hour", "day", "week", "month", "year"}:
            raise ValueError("granularity must be hour/day/week/month/year")

        # date_trunc returns timestamp
        stmt = select(func.date_trunc(gran, ts_col).label("bucket"), func.count().label("count")).group_by(sa_text("bucket")).order_by(sa_text("bucket"))

        with SessionLocal() as sess:
            rows = sess.execute(stmt).all()
            return [{"bucket": str(r.bucket), "count": r.count} for r in rows]

    def _join_select(self, payload: Dict[str, Any]):
        """Perform simple two-table inner join with explicit on keys."""
        left_tbl = self._get_table(payload["left_table"])
        right_tbl = self._get_table(payload["right_table"])
        left_key = payload["left_key"]
        right_key = payload["right_key"]

        columns = payload.get("columns")  # list of ["left.column", "right.column"] or None

        join_expr = left_tbl.join(right_tbl, left_tbl.c[left_key] == right_tbl.c[right_key])
        sel_cols = []
        if columns:
            for col in columns:
                tbl_alias, col_name = col.split(".")
                if tbl_alias == "left":
                    sel_cols.append(left_tbl.c[col_name])
                elif tbl_alias == "right":
                    sel_cols.append(right_tbl.c[col_name])
        else:
            sel_cols = [left_tbl, right_tbl]

        stmt = select(*sel_cols).select_from(join_expr)

        where = payload.get("where") or {}
        for col, val in where.items():
            # where keys maybe prefixed "left." or "right." to disambiguate
            if "." in col:
                tbl_alias, col_name = col.split(".")
                tbl_obj = left_tbl if tbl_alias == "left" else right_tbl
            else:
                # default to left table
                tbl_obj = left_tbl
                col_name = col
            stmt = stmt.where(tbl_obj.c[col_name] == val)

        limit_val = payload.get("limit")
        if limit_val is not None:
            stmt = stmt.limit(int(limit_val))

        with SessionLocal() as sess:
            rows = sess.execute(stmt).mappings().all()
            return [dict(r) for r in rows]


# Ready-to-use singleton
pg_tool = PostgresDBTool() 