"""REST-Endpunkte rund um Lagerbestände."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..dependencies import get_db

router = APIRouter()


@router.get("/levels", response_model=list[schemas.StockLevelRead])
def read_stock_levels(db: Session = Depends(get_db)) -> list[schemas.StockLevelRead]:
    return [schemas.StockLevelRead.model_validate(level) for level in crud.list_stock_levels(db)]


@router.get("/transactions", response_model=list[schemas.InventoryTransactionRead])
def read_transactions(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
) -> list[schemas.InventoryTransactionRead]:
    transactions = crud.list_transactions(db, limit=limit)
    return [schemas.InventoryTransactionRead.model_validate(tx) for tx in transactions]


@router.post("/transactions", response_model=schemas.InventoryTransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction_in: schemas.InventoryTransactionCreate, db: Session = Depends(get_db)
) -> schemas.InventoryTransactionRead:
    try:
        transaction = crud.register_inventory_transaction(db, transaction_in)
    except crud.CRUDException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return schemas.InventoryTransactionRead.model_validate(transaction)


@router.get("/dashboard", response_model=schemas.DashboardMetrics)
def read_dashboard(db: Session = Depends(get_db)) -> schemas.DashboardMetrics:
    return crud.get_inventory_overview(db)
