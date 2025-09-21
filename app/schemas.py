"""Pydantic-Schemas für API und Formvalidierung."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import PurchaseOrderStatus, TransactionType


class ItemBase(BaseModel):
    sku: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    description: str | None = None
    unit_of_measure: str = Field(default="Stk", max_length=32)
    reorder_level: int = Field(default=0, ge=0)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    unit_of_measure: str | None = Field(default=None, max_length=32)
    reorder_level: int | None = Field(default=None, ge=0)


class ItemRead(ItemBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class StorageLocationBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None


class StorageLocationCreate(StorageLocationBase):
    pass


class StorageLocationRead(StorageLocationBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class SupplierBase(BaseModel):
    name: str = Field(..., max_length=255)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=64)
    notes: str | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierRead(SupplierBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class StockLevelRead(BaseModel):
    id: int
    quantity: float
    item: ItemRead
    location: StorageLocationRead

    model_config = ConfigDict(from_attributes=True)


class InventoryTransactionBase(BaseModel):
    item_id: int
    location_id: int
    quantity: float = Field(..., ne=0)
    transaction_type: TransactionType
    reference: str | None = Field(default=None, max_length=128)
    note: str | None = None


class InventoryTransactionCreate(InventoryTransactionBase):
    pass


class InventoryTransactionRead(InventoryTransactionBase):
    id: int
    created_at: datetime
    item: ItemRead
    location: StorageLocationRead

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderLineBase(BaseModel):
    item_id: int | None = None
    description: str | None = None
    ordered_quantity: float = Field(..., gt=0)
    unit_price: float | None = Field(default=None, ge=0)


class PurchaseOrderLineCreate(PurchaseOrderLineBase):
    pass


class PurchaseOrderLineRead(PurchaseOrderLineBase):
    id: int
    received_quantity: float
    item: ItemRead | None = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderReceiveUpdate(BaseModel):
    received_quantity: float = Field(..., ge=0)


class PurchaseOrderBase(BaseModel):
    order_number: str = Field(..., max_length=64)
    supplier_id: int | None = None
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    expected_date: date | None = None
    notes: str | None = None


class PurchaseOrderCreate(PurchaseOrderBase):
    lines: list[PurchaseOrderLineCreate] | None = None


class PurchaseOrderUpdate(BaseModel):
    supplier_id: int | None = None
    status: PurchaseOrderStatus | None = None
    expected_date: date | None = None
    notes: str | None = None


class PurchaseOrderRead(PurchaseOrderBase):
    id: int
    created_at: datetime
    supplier: SupplierRead | None = None
    lines: list[PurchaseOrderLineRead] = []

    model_config = ConfigDict(from_attributes=True)


class InventorySnapshotEntry(BaseModel):
    sku: str
    item_name: str
    location: str
    quantity: float
    unit_of_measure: str


class InventorySnapshot(BaseModel):
    generated_at: datetime
    warehouse: str
    entries: list[InventorySnapshotEntry]


class ERPPurchaseOrderLine(BaseModel):
    sku: str
    name: str
    ordered_quantity: float
    unit_price: float | None = None
    description: str | None = None


class ERPPurchaseOrder(BaseModel):
    order_number: str
    supplier_name: str
    expected_date: date | None = None
    status: PurchaseOrderStatus = PurchaseOrderStatus.RELEASED
    notes: str | None = None
    lines: list[ERPPurchaseOrderLine]


class ERPImportResult(BaseModel):
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    details: list[str] = []


class ERPExportResponse(BaseModel):
    status: str
    transmitted: int = 0
    message: str | None = None


class DashboardMetrics(BaseModel):
    total_items: int
    total_quantity: float
    open_orders: int
    low_stock: list[dict[str, float | str]]
    recent_transactions: list[InventoryTransactionRead]


class PlanningSuggestion(BaseModel):
    """Planungsinformation für einen Artikel."""

    item_id: int
    sku: str
    name: str
    reorder_level: int
    on_hand: float
    on_order: float
    coverage_gap: float
    shortfall: float
    suggested_order: float
    needs_reorder: bool
