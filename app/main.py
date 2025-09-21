"""Einstiegspunkt für die FastAPI-Anwendung."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .database import init_db
from .web import router as web_router


def create_app() -> FastAPI:
    """Erzeugt und konfiguriert die FastAPI-Anwendung."""

    init_db()

    app = FastAPI(title="Lagerverwaltung Maschinenbau", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(web_router)
    app.include_router(api_router, prefix="/api")
    app.mount("/static", StaticFiles(directory="static"), name="static")

    return app


app = create_app()
