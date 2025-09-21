"""Gemeinsame FastAPI-Dependencies."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.orm import Session

from .crud import ensure_default_location
from .database import SessionLocal
from .erp import ERPClient, ERPService


class Settings(BaseSettings):
    """Anwendungskonfiguration."""

    erp_base_url: str | None = None
    erp_api_key: str | None = None

    model_config = SettingsConfigDict(env_prefix="WMS_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_db() -> Session:
    db = SessionLocal()
    try:
        ensure_default_location(db)
        yield db
    finally:
        db.close()


def get_erp_service(settings: Settings = Depends(get_settings)) -> ERPService:
    client = ERPClient(base_url=settings.erp_base_url, api_key=settings.erp_api_key)
    return ERPService(client)
