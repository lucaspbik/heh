"""Routen für die HTML-Weboberfläche."""

from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import crud, schemas
from .dependencies import get_db, get_erp_service
from .erp import ERPService
from .models import PurchaseOrder, PurchaseOrderLine, PurchaseOrderStatus, TransactionType

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="templates")


def _redirect(url: str, **params: str) -> RedirectResponse:
    if params:
        url = f"{url}?{urlencode(params)}"
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    metrics = crud.get_inventory_overview(db)
    context = {
        "request": request,
        "metrics": metrics,
        "message": message,
        "error": error,
    }
    return templates.TemplateResponse("dashboard.html", context)


@router.get("/planning", response_class=HTMLResponse)
def show_planning(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    suggestions = crud.get_planning_overview(db)
    monitored = [entry for entry in suggestions if entry.reorder_level > 0]
    needs_reorder = [entry for entry in monitored if entry.needs_reorder]

    open_orders_data: list[dict[str, object]] = []
    for order in crud.list_purchase_orders(db):
        if order.status in {PurchaseOrderStatus.CANCELLED, PurchaseOrderStatus.COMPLETED}:
            continue
        remaining = 0.0
        outstanding_lines = 0
        for line in order.lines:
            ordered = float(line.ordered_quantity or 0)
            received = float(line.received_quantity or 0)
            open_quantity = ordered - received
            if open_quantity > 0:
                outstanding_lines += 1
                remaining += open_quantity
        if outstanding_lines == 0 and remaining <= 0:
            continue
        open_orders_data.append(
            {
                "order": order,
                "remaining": remaining,
                "outstanding_lines": outstanding_lines,
            }
        )

    open_orders_data.sort(
        key=lambda entry: (
            entry["order"].expected_date or date.max,
            entry["order"].order_number,
        )
    )

    summary = {
        "total_items": len(monitored) if monitored else len(suggestions),
        "needs_reorder": len(needs_reorder),
        "recommended_quantity": sum(entry.suggested_order for entry in needs_reorder),
        "open_orders": len(open_orders_data),
    }

    context = {
        "request": request,
        "suggestions": suggestions,
        "summary": summary,
        "open_orders": open_orders_data,
        "message": message,
        "error": error,
    }
    return templates.TemplateResponse("planning/overview.html", context)


@router.get("/items", response_class=HTMLResponse)
def show_items(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    items = crud.list_items(db)
    context = {
        "request": request,
        "items": items,
        "message": message,
        "error": error,
    }
    return templates.TemplateResponse("items/list.html", context)


@router.post("/items")
async def create_item(
    request: Request,
    sku: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    unit_of_measure: str = Form("Stk"),
    reorder_level: int = Form(0),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    item_in = schemas.ItemCreate(
        sku=sku,
        name=name,
        description=description or None,
        unit_of_measure=unit_of_measure,
        reorder_level=reorder_level,
    )
    try:
        crud.create_item(db, item_in)
    except crud.CRUDException as exc:
        context = {
            "request": request,
            "items": crud.list_items(db),
            "error": str(exc),
        }
        return templates.TemplateResponse("items/list.html", context, status_code=status.HTTP_400_BAD_REQUEST)
    return _redirect(router.url_path_for("show_items"), message="Artikel angelegt")


@router.get("/locations", response_class=HTMLResponse)
def show_locations(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    locations = crud.list_locations(db)
    context = {
        "request": request,
        "locations": locations,
        "message": message,
        "error": error,
    }
    return templates.TemplateResponse("locations/list.html", context)


@router.post("/locations")
async def create_location(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    location_in = schemas.StorageLocationCreate(name=name, description=description or None)
    try:
        crud.create_location(db, location_in)
    except crud.CRUDException as exc:
        context = {
            "request": request,
            "locations": crud.list_locations(db),
            "error": str(exc),
        }
        return templates.TemplateResponse("locations/list.html", context, status_code=status.HTTP_400_BAD_REQUEST)
    return _redirect(router.url_path_for("show_locations"), message="Lagerort angelegt")


@router.get("/suppliers", response_class=HTMLResponse)
def show_suppliers(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    suppliers = crud.list_suppliers(db)
    context = {
        "request": request,
        "suppliers": suppliers,
        "message": message,
        "error": error,
    }
    return templates.TemplateResponse("suppliers/list.html", context)


@router.post("/suppliers")
async def create_supplier(
    request: Request,
    name: str = Form(...),
    contact_email: str = Form(""),
    contact_phone: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    supplier_in = schemas.SupplierCreate(
        name=name,
        contact_email=contact_email or None,
        contact_phone=contact_phone or None,
        notes=notes or None,
    )
    try:
        crud.create_supplier(db, supplier_in)
    except crud.CRUDException as exc:
        context = {
            "request": request,
            "suppliers": crud.list_suppliers(db),
            "error": str(exc),
        }
        return templates.TemplateResponse("suppliers/list.html", context, status_code=status.HTTP_400_BAD_REQUEST)
    return _redirect(router.url_path_for("show_suppliers"), message="Lieferant angelegt")


@router.get("/inventory", response_class=HTMLResponse)
def show_inventory(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    context = {
        "request": request,
        "stock_levels": crud.list_stock_levels(db),
        "items": crud.list_items(db),
        "locations": crud.list_locations(db),
        "transactions": crud.list_transactions(db, limit=15),
        "transaction_types": list(TransactionType),
        "message": message,
        "error": error,
    }
    return templates.TemplateResponse("inventory/list.html", context)


@router.post("/inventory/movements")
async def create_inventory_movement(
    request: Request,
    item_id: int = Form(...),
    location_id: int = Form(...),
    quantity: float = Form(...),
    transaction_type: str = Form(...),
    reference: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        movement = schemas.InventoryTransactionCreate(
            item_id=item_id,
            location_id=location_id,
            quantity=quantity,
            transaction_type=TransactionType(transaction_type),
            reference=reference or None,
            note=note or None,
        )
        crud.register_inventory_transaction(db, movement)
    except (ValueError, crud.CRUDException) as exc:
        context = {
            "request": request,
            "stock_levels": crud.list_stock_levels(db),
            "items": crud.list_items(db),
            "locations": crud.list_locations(db),
            "transactions": crud.list_transactions(db, limit=15),
            "transaction_types": list(TransactionType),
            "error": str(exc),
        }
        return templates.TemplateResponse("inventory/list.html", context, status_code=status.HTTP_400_BAD_REQUEST)
    return _redirect(router.url_path_for("show_inventory"), message="Bewegung erfasst")


@router.get("/purchase-orders", response_class=HTMLResponse)
def show_purchase_orders(
    request: Request,
    message: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    context = {
        "request": request,
        "orders": crud.list_purchase_orders(db),
        "suppliers": crud.list_suppliers(db),
        "items": crud.list_items(db),
        "status_values": list(PurchaseOrderStatus),
        "message": message,
        "error": error,
    }
    return templates.TemplateResponse("purchase_orders/list.html", context)


@router.post("/purchase-orders")
async def create_purchase_order(
    request: Request,
    order_number: str = Form(...),
    supplier_id: str = Form(""),
    status_value: str = Form(PurchaseOrderStatus.RELEASED.value),
    expected_date: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    supplier_id_value = int(supplier_id) if supplier_id else None
    expected = date.fromisoformat(expected_date) if expected_date else None
    order_in = schemas.PurchaseOrderCreate(
        order_number=order_number,
        supplier_id=supplier_id_value,
        status=PurchaseOrderStatus(status_value),
        expected_date=expected,
        notes=notes or None,
    )
    try:
        crud.create_purchase_order(db, order_in)
    except (ValueError, crud.CRUDException) as exc:
        context = {
            "request": request,
            "orders": crud.list_purchase_orders(db),
            "suppliers": crud.list_suppliers(db),
            "items": crud.list_items(db),
            "status_values": list(PurchaseOrderStatus),
            "error": str(exc),
        }
        return templates.TemplateResponse("purchase_orders/list.html", context, status_code=status.HTTP_400_BAD_REQUEST)
    return _redirect(router.url_path_for("show_purchase_orders"), message="Bestellung angelegt")


@router.post("/purchase-orders/{order_id}/lines")
async def add_purchase_order_line(
    order_id: int,
    request: Request,
    item_id: str = Form(""),
    description: str = Form(""),
    ordered_quantity: float = Form(...),
    unit_price: str = Form(""),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    order = db.get(PurchaseOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bestellung nicht gefunden")
    item_id_value = int(item_id) if item_id else None
    unit_price_value = float(unit_price) if unit_price else None
    line_in = schemas.PurchaseOrderLineCreate(
        item_id=item_id_value,
        description=description or None,
        ordered_quantity=ordered_quantity,
        unit_price=unit_price_value,
    )
    try:
        crud.add_purchase_order_line(db, order, line_in)
    except crud.CRUDException as exc:
        context = {
            "request": request,
            "orders": crud.list_purchase_orders(db),
            "suppliers": crud.list_suppliers(db),
            "items": crud.list_items(db),
            "status_values": list(PurchaseOrderStatus),
            "error": str(exc),
        }
        return templates.TemplateResponse("purchase_orders/list.html", context, status_code=status.HTTP_400_BAD_REQUEST)
    return _redirect(router.url_path_for("show_purchase_orders"), message="Position hinzugefügt")


@router.post("/purchase-orders/{order_id}/receive")
async def receive_purchase_order(
    order_id: int,
    request: Request,
    line_id: int = Form(...),
    received_quantity: float = Form(...),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    line = db.get(PurchaseOrderLine, line_id)
    if not line:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bestellposition nicht gefunden")
    try:
        crud.set_purchase_order_line_received(db, line, received_quantity)
    except crud.CRUDException as exc:
        context = {
            "request": request,
            "orders": crud.list_purchase_orders(db),
            "suppliers": crud.list_suppliers(db),
            "items": crud.list_items(db),
            "status_values": list(PurchaseOrderStatus),
            "error": str(exc),
        }
        return templates.TemplateResponse("purchase_orders/list.html", context, status_code=status.HTTP_400_BAD_REQUEST)
    return _redirect(router.url_path_for("show_purchase_orders"), message="Wareneingang aktualisiert")


@router.post("/erp/export")
async def trigger_erp_export(
    service: ERPService = Depends(get_erp_service),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    result = await service.push_inventory_snapshot(db)
    return _redirect(router.url_path_for("dashboard"), message=f"ERP-Export: {result.status}")


@router.post("/erp/sync")
async def trigger_erp_sync(
    service: ERPService = Depends(get_erp_service),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    result = await service.sync_purchase_orders(db)
    message = f"Importiert: {result.imported}, Aktualisiert: {result.updated}, Übersprungen: {result.skipped}"
    return _redirect(router.url_path_for("dashboard"), message=message)
