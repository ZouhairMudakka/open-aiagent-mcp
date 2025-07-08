from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from pathlib import Path

# Default to local SQLite if DATABASE_URL not set
DEFAULT_SQLITE = "sqlite:///" + str(Path("data/sample.db").absolute())
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))

Base = declarative_base()


def init_db():
    """Call once on startup to create tables."""
    from . import models  # noqa: F401  # ensure models are imported

    Base.metadata.create_all(bind=engine) 