"""Datenbankkonfiguration und Session-Verwaltung."""

from __future__ import annotations

import os
from typing import Any, Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./warehouse.db")

_engine_kwargs: Dict[str, Any] = {}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


def init_db() -> None:
    """Initialisiert die Datenbanktabellen."""
    # Import erst innerhalb der Funktion, um zirkuläre Importe zu vermeiden.
    from . import models  # noqa: WPS433  # pylint: disable=import-outside-toplevel

    models  # nur zum Registrieren der Modelle benötigt
    Base.metadata.create_all(bind=engine)
