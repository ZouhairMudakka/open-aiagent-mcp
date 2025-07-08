from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import select, delete, update
from sqlalchemy.exc import SQLAlchemyError

from ..db.session import SessionLocal, init_db
from ..db.models import Record


class DBTool:
    """Database-agnostic CRUD tool using SQLAlchemy.

    Works with Postgres, SQLite, etc. `DATABASE_URL` decides backend.
    """

    def __init__(self):
        # Ensure tables exist on first use
        init_db()

    # ------------------------------------------------------------------
    def __call__(self, payload: Dict[str, Any]):
        action = payload.get("action")
        with SessionLocal() as session:
            try:
                if action == "add":
                    rec = Record(data=str(payload.get("data", "")))
                    session.add(rec)
                    session.commit()
                    session.refresh(rec)
                    return {"id": rec.id, "data": rec.data}

                if action == "delete":
                    stmt = delete(Record).where(Record.id == int(payload["id"]))
                    res = session.execute(stmt)
                    session.commit()
                    return {"deleted": res.rowcount}

                if action == "update":
                    stmt = (
                        update(Record)
                        .where(Record.id == int(payload["id"]))
                        .values(data=str(payload.get("data", "")))
                    )
                    res = session.execute(stmt)
                    session.commit()
                    return {"updated": res.rowcount}

                if action == "list":
                    stmt = select(Record)
                    recs = session.execute(stmt).scalars().all()
                    return [{"id": r.id, "data": r.data} for r in recs]

            except SQLAlchemyError as exc:
                session.rollback()
                raise RuntimeError(str(exc)) from exc

        raise ValueError("Unsupported DB action; choose add/delete/update/list") 