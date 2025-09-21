"""REST-Endpunkte für Lagerorte."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..dependencies import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.StorageLocationRead])
def read_locations(db: Session = Depends(get_db)) -> list[schemas.StorageLocationRead]:
    return [schemas.StorageLocationRead.model_validate(location) for location in crud.list_locations(db)]


@router.post("/", response_model=schemas.StorageLocationRead, status_code=status.HTTP_201_CREATED)
def create_location(
    location_in: schemas.StorageLocationCreate, db: Session = Depends(get_db)
) -> schemas.StorageLocationRead:
    try:
        location = crud.create_location(db, location_in)
    except crud.CRUDException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return schemas.StorageLocationRead.model_validate(location)
