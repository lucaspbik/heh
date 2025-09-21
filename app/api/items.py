"""REST-Endpunkte für Artikel."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..dependencies import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.ItemRead])
def read_items(db: Session = Depends(get_db)) -> list[schemas.ItemRead]:
    return [schemas.ItemRead.model_validate(item) for item in crud.list_items(db)]


@router.post("/", response_model=schemas.ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(item_in: schemas.ItemCreate, db: Session = Depends(get_db)) -> schemas.ItemRead:
    try:
        item = crud.create_item(db, item_in)
    except crud.CRUDException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return schemas.ItemRead.model_validate(item)


@router.get("/{item_id}", response_model=schemas.ItemRead)
def read_item(item_id: int, db: Session = Depends(get_db)) -> schemas.ItemRead:
    item = crud.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artikel nicht gefunden")
    return schemas.ItemRead.model_validate(item)


@router.put("/{item_id}", response_model=schemas.ItemRead)
def update_item(item_id: int, item_in: schemas.ItemUpdate, db: Session = Depends(get_db)) -> schemas.ItemRead:
    item = crud.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artikel nicht gefunden")
    item = crud.update_item(db, item, item_in)
    return schemas.ItemRead.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)) -> None:
    item = crud.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artikel nicht gefunden")
    crud.delete_item(db, item)
