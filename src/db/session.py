from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from pathlib import Path

# Require DATABASE_URL; fall back to common docker-compose Postgres URL for dev
# Raise explicit error if not provided so we avoid accidentally using SQLite.

DEFAULT_PG = "postgresql+psycopg2://postgres:postgres@localhost:5433/agentic"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_PG)

if DATABASE_URL.startswith("sqlite"):
    raise RuntimeError(
        "SQLite backend is no longer supported. Set DATABASE_URL to a Postgres connection string "
        "(e.g. postgresql+psycopg2://postgres:postgres@localhost:5432/agentic)."
    )

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))

Base = declarative_base()


def init_db():
    """Call once on startup to create tables."""
    from . import models  # noqa: F401  # ensure models are imported

    Base.metadata.create_all(bind=engine) 