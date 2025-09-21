"""REST-Endpunkte für Lieferanten."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..dependencies import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.SupplierRead])
def read_suppliers(db: Session = Depends(get_db)) -> list[schemas.SupplierRead]:
    return [schemas.SupplierRead.model_validate(supplier) for supplier in crud.list_suppliers(db)]


@router.post("/", response_model=schemas.SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(
    supplier_in: schemas.SupplierCreate, db: Session = Depends(get_db)
) -> schemas.SupplierRead:
    try:
        supplier = crud.create_supplier(db, supplier_in)
    except crud.CRUDException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return schemas.SupplierRead.model_validate(supplier)
