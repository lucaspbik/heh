"""REST-Endpunkte für Bestellungen."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..dependencies import get_db
from ..models import PurchaseOrder, PurchaseOrderLine

router = APIRouter()


@router.get("/", response_model=list[schemas.PurchaseOrderRead])
def read_purchase_orders(db: Session = Depends(get_db)) -> list[schemas.PurchaseOrderRead]:
    orders = crud.list_purchase_orders(db)
    return [schemas.PurchaseOrderRead.model_validate(order) for order in orders]


@router.post("/", response_model=schemas.PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    order_in: schemas.PurchaseOrderCreate, db: Session = Depends(get_db)
) -> schemas.PurchaseOrderRead:
    try:
        order = crud.create_purchase_order(db, order_in)
    except crud.CRUDException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return schemas.PurchaseOrderRead.model_validate(order)


@router.put("/{order_id}", response_model=schemas.PurchaseOrderRead)
def update_purchase_order(
    order_id: int, order_in: schemas.PurchaseOrderUpdate, db: Session = Depends(get_db)
) -> schemas.PurchaseOrderRead:
    order = db.get(PurchaseOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bestellung nicht gefunden")
    order = crud.update_purchase_order(db, order, order_in)
    return schemas.PurchaseOrderRead.model_validate(order)


@router.post("/{order_id}/lines", response_model=schemas.PurchaseOrderLineRead, status_code=status.HTTP_201_CREATED)
def add_purchase_order_line(
    order_id: int, line_in: schemas.PurchaseOrderLineCreate, db: Session = Depends(get_db)
) -> schemas.PurchaseOrderLineRead:
    order = db.get(PurchaseOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bestellung nicht gefunden")
    try:
        line = crud.add_purchase_order_line(db, order, line_in)
    except crud.CRUDException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return schemas.PurchaseOrderLineRead.model_validate(line)


@router.post("/lines/{line_id}/received", response_model=schemas.PurchaseOrderLineRead)
def set_line_received(
    line_id: int,
    payload: schemas.PurchaseOrderReceiveUpdate,
    db: Session = Depends(get_db),
) -> schemas.PurchaseOrderLineRead:
    line = db.get(PurchaseOrderLine, line_id)
    if not line:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bestellposition nicht gefunden")
    try:
        updated_line = crud.set_purchase_order_line_received(db, line, payload.received_quantity)
    except crud.CRUDException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return schemas.PurchaseOrderLineRead.model_validate(updated_line)
