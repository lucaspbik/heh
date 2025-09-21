"""REST-Endpunkte für den ERP-Datenaustausch."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..dependencies import get_db, get_erp_service
from ..erp import ERPService

router = APIRouter()


@router.post("/export/inventory", response_model=schemas.ERPExportResponse)
async def export_inventory(
    db: Session = Depends(get_db), service: ERPService = Depends(get_erp_service)
) -> schemas.ERPExportResponse:
    return await service.push_inventory_snapshot(db)


@router.post("/sync/purchase-orders", response_model=schemas.ERPImportResult)
async def sync_purchase_orders(
    db: Session = Depends(get_db), service: ERPService = Depends(get_erp_service)
) -> schemas.ERPImportResult:
    return await service.sync_purchase_orders(db)


@router.post("/ingest/purchase-orders", response_model=schemas.ERPImportResult)
def ingest_purchase_orders(
    payload: list[schemas.ERPPurchaseOrder],
    db: Session = Depends(get_db),
    service: ERPService = Depends(get_erp_service),
) -> schemas.ERPImportResult:
    return service.import_purchase_orders(db, list(payload))
