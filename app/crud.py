"""Geschäftslogik und Datenbankoperationen."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from . import schemas
from .models import (
    InventoryTransaction,
    Item,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
    StockLevel,
    StorageLocation,
    Supplier,
    TransactionType,
)


class CRUDException(RuntimeError):
    """Basisausnahme für CRUD-Operationen."""


def list_items(db: Session) -> list[Item]:
    return db.query(Item).order_by(Item.name).all()


def get_item(db: Session, item_id: int) -> Item | None:
    return db.get(Item, item_id)


def create_item(db: Session, item_in: schemas.ItemCreate) -> Item:
    if db.query(Item).filter(Item.sku == item_in.sku).first():
        raise CRUDException("Artikelnummer existiert bereits.")
    item = Item(
        sku=item_in.sku,
        name=item_in.name,
        description=item_in.description,
        unit_of_measure=item_in.unit_of_measure,
        reorder_level=item_in.reorder_level,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, item: Item, item_in: schemas.ItemUpdate) -> Item:
    for field in ("name", "description", "unit_of_measure", "reorder_level"):
        value = getattr(item_in, field)
        if value is not None:
            setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item: Item) -> None:
    db.delete(item)
    db.commit()


def list_locations(db: Session) -> list[StorageLocation]:
    return db.query(StorageLocation).order_by(StorageLocation.name).all()


def create_location(db: Session, location_in: schemas.StorageLocationCreate) -> StorageLocation:
    if db.query(StorageLocation).filter(StorageLocation.name == location_in.name).first():
        raise CRUDException("Lagerort existiert bereits.")
    location = StorageLocation(name=location_in.name, description=location_in.description)
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def ensure_default_location(db: Session) -> StorageLocation:
    location = db.query(StorageLocation).order_by(StorageLocation.id).first()
    if location:
        return location
    location = StorageLocation(name="Hauptlager", description="Automatisch erzeugter Standardlagerort")
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def list_suppliers(db: Session) -> list[Supplier]:
    return db.query(Supplier).order_by(Supplier.name).all()


def create_supplier(db: Session, supplier_in: schemas.SupplierCreate) -> Supplier:
    if db.query(Supplier).filter(Supplier.name == supplier_in.name).first():
        raise CRUDException("Lieferant existiert bereits.")
    supplier = Supplier(
        name=supplier_in.name,
        contact_email=supplier_in.contact_email,
        contact_phone=supplier_in.contact_phone,
        notes=supplier_in.notes,
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def get_supplier_by_name(db: Session, name: str) -> Supplier | None:
    return db.query(Supplier).filter(func.lower(Supplier.name) == func.lower(name)).first()


def list_stock_levels(db: Session) -> list[StockLevel]:
    return (
        db.query(StockLevel)
        .options(selectinload(StockLevel.item), selectinload(StockLevel.location))
        .order_by(StockLevel.id)
        .all()
    )


def get_stock_level(db: Session, item_id: int, location_id: int) -> StockLevel | None:
    return (
        db.query(StockLevel)
        .filter(StockLevel.item_id == item_id, StockLevel.location_id == location_id)
        .first()
    )


def register_inventory_transaction(
    db: Session, transaction_in: schemas.InventoryTransactionCreate
) -> InventoryTransaction:
    item = db.get(Item, transaction_in.item_id)
    location = db.get(StorageLocation, transaction_in.location_id)
    if not item or not location:
        raise CRUDException("Artikel oder Lagerort wurde nicht gefunden.")

    if transaction_in.quantity == 0:
        raise CRUDException("Die Bewegungsmenge darf nicht 0 sein.")

    stock_level = get_stock_level(db, item.id, location.id)
    if not stock_level:
        stock_level = StockLevel(item=item, location=location, quantity=0)
        db.add(stock_level)
        db.flush()

    quantity_delta = float(transaction_in.quantity)

    if transaction_in.transaction_type == TransactionType.RECEIPT:
        if quantity_delta <= 0:
            raise CRUDException("Wareneingang benötigt eine positive Menge.")
        stock_level.quantity += quantity_delta
    elif transaction_in.transaction_type == TransactionType.SHIPMENT:
        if quantity_delta <= 0:
            raise CRUDException("Warenausgang benötigt eine positive Menge.")
        if stock_level.quantity - quantity_delta < 0:
            raise CRUDException("Der Bestand darf nicht negativ werden.")
        stock_level.quantity -= quantity_delta
    elif transaction_in.transaction_type == TransactionType.ADJUSTMENT:
        # Bei Anpassungen wird die delta-Menge angewendet (kann positiv oder negativ sein).
        new_quantity = stock_level.quantity + quantity_delta
        if new_quantity < 0:
            raise CRUDException("Der Bestand darf nicht negativ werden.")
        stock_level.quantity = new_quantity
    else:  # pragma: no cover - sollte durch Enum abgesichert sein
        raise CRUDException("Unbekannter Bewegungstyp")

    transaction = InventoryTransaction(
        item=item,
        location=location,
        quantity=quantity_delta,
        transaction_type=transaction_in.transaction_type,
        reference=transaction_in.reference,
        note=transaction_in.note,
        created_at=datetime.utcnow(),
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def list_transactions(db: Session, limit: int = 20) -> list[InventoryTransaction]:
    return (
        db.query(InventoryTransaction)
        .options(selectinload(InventoryTransaction.item), selectinload(InventoryTransaction.location))
        .order_by(InventoryTransaction.created_at.desc())
        .limit(limit)
        .all()
    )


def get_inventory_overview(db: Session) -> schemas.DashboardMetrics:
    total_items = db.query(func.count(Item.id)).scalar() or 0
    total_quantity = db.query(func.coalesce(func.sum(StockLevel.quantity), 0)).scalar() or 0
    open_orders = (
        db.query(func.count(PurchaseOrder.id))
        .filter(PurchaseOrder.status != PurchaseOrderStatus.COMPLETED)
        .scalar()
        or 0
    )

    low_stock_rows = (
        db.query(
            Item,
            func.coalesce(func.sum(StockLevel.quantity), 0).label("quantity"),
        )
        .outerjoin(StockLevel)
        .group_by(Item.id)
        .having(func.coalesce(func.sum(StockLevel.quantity), 0) <= Item.reorder_level)
        .order_by(Item.name)
        .all()
    )
    low_stock = [
        {
            "item_id": row.Item.id,
            "sku": row.Item.sku,
            "name": row.Item.name,
            "quantity": float(row.quantity),
            "reorder_level": row.Item.reorder_level,
        }
        for row in low_stock_rows
    ]

    recent_transactions = list_transactions(db, limit=10)

    return schemas.DashboardMetrics(
        total_items=total_items,
        total_quantity=float(total_quantity),
        open_orders=open_orders,
        low_stock=low_stock,
        recent_transactions=[schemas.InventoryTransactionRead.model_validate(tx) for tx in recent_transactions],
    )


def create_purchase_order(db: Session, order_in: schemas.PurchaseOrderCreate) -> PurchaseOrder:
    if db.query(PurchaseOrder).filter(PurchaseOrder.order_number == order_in.order_number).first():
        raise CRUDException("Bestellnummer existiert bereits.")
    purchase_order = PurchaseOrder(
        order_number=order_in.order_number,
        supplier_id=order_in.supplier_id,
        status=order_in.status,
        expected_date=order_in.expected_date,
        notes=order_in.notes,
    )
    if order_in.lines:
        for line_in in order_in.lines:
            line = _build_purchase_order_line(db, line_in)
            purchase_order.lines.append(line)
    db.add(purchase_order)
    db.commit()
    db.refresh(purchase_order)
    return purchase_order


def update_purchase_order(
    db: Session, purchase_order: PurchaseOrder, order_in: schemas.PurchaseOrderUpdate
) -> PurchaseOrder:
    for field in ("supplier_id", "status", "expected_date", "notes"):
        value = getattr(order_in, field)
        if value is not None:
            setattr(purchase_order, field, value)
    db.add(purchase_order)
    db.commit()
    db.refresh(purchase_order)
    return purchase_order


def add_purchase_order_line(
    db: Session, purchase_order: PurchaseOrder, line_in: schemas.PurchaseOrderLineCreate
) -> PurchaseOrderLine:
    line = _build_purchase_order_line(db, line_in)
    purchase_order.lines.append(line)
    db.add(purchase_order)
    db.commit()
    db.refresh(line)
    return line


def list_purchase_orders(db: Session) -> list[PurchaseOrder]:
    return (
        db.query(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.lines).selectinload(PurchaseOrderLine.item),
        )
        .order_by(PurchaseOrder.created_at.desc())
        .all()
    )


def set_purchase_order_line_received(
    db: Session, line: PurchaseOrderLine, received_quantity: float
) -> PurchaseOrderLine:
    if received_quantity < 0:
        raise CRUDException("Gelieferte Menge darf nicht negativ sein.")
    line.received_quantity = received_quantity
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def get_purchase_order_by_number(db: Session, order_number: str) -> PurchaseOrder | None:
    return db.query(PurchaseOrder).filter(PurchaseOrder.order_number == order_number).first()


def get_purchase_order_line(db: Session, line_id: int) -> PurchaseOrderLine | None:
    return db.get(PurchaseOrderLine, line_id)


def _build_purchase_order_line(
    db: Session, line_in: schemas.PurchaseOrderLineCreate
) -> PurchaseOrderLine:
    item = None
    if line_in.item_id is not None:
        item = db.get(Item, line_in.item_id)
        if not item:
            raise CRUDException("Artikel für Bestellposition nicht gefunden.")
    return PurchaseOrderLine(
        item=item,
        description=line_in.description,
        ordered_quantity=line_in.ordered_quantity,
        unit_price=line_in.unit_price,
    )


def get_or_create_item_by_sku(db: Session, sku: str, defaults: dict[str, Any] | None = None) -> Item:
    item = db.query(Item).filter(Item.sku == sku).first()
    if item:
        return item
    defaults = defaults or {}
    item = Item(
        sku=sku,
        name=defaults.get("name", sku),
        description=defaults.get("description"),
        unit_of_measure=defaults.get("unit_of_measure", "Stk"),
        reorder_level=int(defaults.get("reorder_level", 0)),
    )
    db.add(item)
    db.flush()
    return item


def get_or_create_supplier_by_name(db: Session, name: str) -> Supplier:
    supplier = get_supplier_by_name(db, name)
    if supplier:
        return supplier
    supplier = Supplier(name=name)
    db.add(supplier)
    db.flush()
    return supplier


def import_purchase_orders_from_payload(
    db: Session, payload: Iterable[schemas.ERPPurchaseOrder]
) -> schemas.ERPImportResult:
    imported = 0
    updated = 0
    skipped = 0
    details: list[str] = []

    for order in payload:
        supplier = get_or_create_supplier_by_name(db, order.supplier_name)
        existing = get_purchase_order_by_number(db, order.order_number)

        if existing is None:
            purchase_order = PurchaseOrder(
                order_number=order.order_number,
                supplier=supplier,
                status=order.status,
                expected_date=order.expected_date,
                notes=order.notes,
            )
            _replace_purchase_order_lines(db, purchase_order, order.lines)
            db.add(purchase_order)
            imported += 1
        else:
            existing.supplier = supplier
            existing.status = order.status
            existing.expected_date = order.expected_date
            existing.notes = order.notes
            _replace_purchase_order_lines(db, existing, order.lines)
            updated += 1

        try:
            db.commit()
        except IntegrityError as exc:  # pragma: no cover - Fehlerfall
            db.rollback()
            skipped += 1
            details.append(f"Bestellung {order.order_number} konnte nicht gespeichert werden: {exc!s}")

    return schemas.ERPImportResult(imported=imported, updated=updated, skipped=skipped, details=details)


def _replace_purchase_order_lines(
    db: Session, purchase_order: PurchaseOrder, lines: Iterable[schemas.ERPPurchaseOrderLine]
) -> None:
    purchase_order.lines.clear()
    for line in lines:
        item = get_or_create_item_by_sku(
            db,
            line.sku,
            {
                "name": line.name,
                "description": line.description,
            },
        )
        purchase_order.lines.append(
            PurchaseOrderLine(
                item=item,
                description=line.description,
                ordered_quantity=line.ordered_quantity,
                unit_price=line.unit_price,
            )
        )
    db.flush()
