"""SQLAlchemy-Modelle für das Lagerverwaltungssystem."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TransactionType(str, enum.Enum):
    """Mögliche Arten von Lagerbewegungen."""

    RECEIPT = "receipt"
    SHIPMENT = "shipment"
    ADJUSTMENT = "adjustment"


class PurchaseOrderStatus(str, enum.Enum):
    """Status einer Bestellung."""

    DRAFT = "draft"
    RELEASED = "released"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Item(Base):
    """Artikelstammdaten."""

    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("sku", name="uq_items_sku"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    unit_of_measure: Mapped[str] = mapped_column(String(32), default="Stk", nullable=False)
    reorder_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    stock_levels: Mapped[list["StockLevel"]] = relationship(
        "StockLevel", back_populates="item", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["InventoryTransaction"]] = relationship(
        "InventoryTransaction", back_populates="item", cascade="all, delete-orphan"
    )
    purchase_order_lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine", back_populates="item"
    )


class StorageLocation(Base):
    """Lagerort innerhalb des Unternehmens."""

    __tablename__ = "storage_locations"
    __table_args__ = (UniqueConstraint("name", name="uq_storage_locations_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())

    stock_levels: Mapped[list["StockLevel"]] = relationship(
        "StockLevel", back_populates="location", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["InventoryTransaction"]] = relationship(
        "InventoryTransaction", back_populates="location", cascade="all, delete-orphan"
    )


class Supplier(Base):
    """Lieferant für Bestellungen."""

    __tablename__ = "suppliers"
    __table_args__ = (UniqueConstraint("name", name="uq_suppliers_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text())

    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        "PurchaseOrder", back_populates="supplier"
    )


class StockLevel(Base):
    """Bestand eines Artikels an einem konkreten Lagerort."""

    __tablename__ = "stock_levels"
    __table_args__ = (
        UniqueConstraint("item_id", "location_id", name="uq_stock_levels_item_location"),
        CheckConstraint("quantity >= 0", name="ck_stock_levels_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("storage_locations.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    item: Mapped[Item] = relationship("Item", back_populates="stock_levels")
    location: Mapped[StorageLocation] = relationship("StorageLocation", back_populates="stock_levels")


class InventoryTransaction(Base):
    """Historie einzelner Lagerbewegungen."""

    __tablename__ = "inventory_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("storage_locations.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(128))
    note: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    item: Mapped[Item] = relationship("Item", back_populates="transactions")
    location: Mapped[StorageLocation] = relationship("StorageLocation", back_populates="transactions")


class PurchaseOrder(Base):
    """Bestellkopf für externe Beschaffung."""

    __tablename__ = "purchase_orders"
    __table_args__ = (UniqueConstraint("order_number", name="uq_purchase_orders_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(64), nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        Enum(PurchaseOrderStatus), default=PurchaseOrderStatus.DRAFT, nullable=False
    )
    expected_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    supplier: Mapped[Supplier | None] = relationship("Supplier", back_populates="purchase_orders")
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine", back_populates="purchase_order", cascade="all, delete-orphan"
    )


class PurchaseOrderLine(Base):
    """Position innerhalb einer Bestellung."""

    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"))
    description: Mapped[str | None] = mapped_column(Text())
    ordered_quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    received_quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    unit_price: Mapped[float | None] = mapped_column(Float)

    purchase_order: Mapped[PurchaseOrder] = relationship("PurchaseOrder", back_populates="lines")
    item: Mapped[Item | None] = relationship("Item", back_populates="purchase_order_lines")
