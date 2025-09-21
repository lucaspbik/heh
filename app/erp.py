"""ERP-Integration für den Datenaustausch."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from . import crud, schemas

LOGGER = logging.getLogger(__name__)


class ERPClient:
    """Asynchrone Kommunikation mit einem ERP-System."""

    def __init__(self, base_url: str | None, api_key: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.api_key = api_key
        self.timeout = timeout

    async def push_inventory_snapshot(self, snapshot: schemas.InventorySnapshot) -> schemas.ERPExportResponse:
        if not self.base_url:
            return schemas.ERPExportResponse(
                status="disabled",
                transmitted=0,
                message="ERP-Basis-URL ist nicht konfiguriert.",
            )
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._build_headers(),
            ) as client:
                response = await client.post("/inventory/sync", json=snapshot.model_dump())
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:  # pragma: no cover - Netzwerkausnahme
            LOGGER.warning("Fehler beim Senden an das ERP: %s", exc)
            return schemas.ERPExportResponse(status="error", transmitted=0, message=str(exc))

        transmitted = int(data.get("transmitted", len(snapshot.entries))) if isinstance(data, dict) else len(snapshot.entries)
        status = data.get("status", "ok") if isinstance(data, dict) else "ok"
        message = data.get("message") if isinstance(data, dict) else None
        return schemas.ERPExportResponse(status=status, transmitted=transmitted, message=message)

    async def fetch_purchase_orders(self) -> list[dict[str, Any]]:
        if not self.base_url:
            return []
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._build_headers(),
            ) as client:
                response = await client.get("/purchase-orders/open")
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:  # pragma: no cover - Netzwerkausnahme
            LOGGER.warning("Fehler beim Abrufen aus dem ERP: %s", exc)
            return []

        if isinstance(payload, dict):
            orders = payload.get("orders", [])
            if isinstance(orders, list):
                return orders
            LOGGER.warning("Ungültige ERP-Antwortstruktur: %s", payload)
            return []
        if isinstance(payload, list):
            return payload
        LOGGER.warning("Unbekannter ERP-Antworttyp: %s", type(payload))
        return []

    def _build_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


class ERPService:
    """Geschäftslogik rund um den ERP-Datenaustausch."""

    def __init__(self, client: ERPClient) -> None:
        self.client = client

    def build_inventory_snapshot(self, db) -> schemas.InventorySnapshot:
        entries: list[schemas.InventorySnapshotEntry] = []
        for level in crud.list_stock_levels(db):
            entries.append(
                schemas.InventorySnapshotEntry(
                    sku=level.item.sku,
                    item_name=level.item.name,
                    location=level.location.name,
                    quantity=float(level.quantity),
                    unit_of_measure=level.item.unit_of_measure,
                )
            )
        return schemas.InventorySnapshot(
            generated_at=datetime.utcnow(),
            warehouse="Maschinenbau-Zentrallager",
            entries=entries,
        )

    async def push_inventory_snapshot(self, db) -> schemas.ERPExportResponse:
        snapshot = self.build_inventory_snapshot(db)
        return await self.client.push_inventory_snapshot(snapshot)

    async def fetch_purchase_orders(self) -> list[schemas.ERPPurchaseOrder]:
        raw_orders = await self.client.fetch_purchase_orders()
        orders: list[schemas.ERPPurchaseOrder] = []
        for raw_order in raw_orders:
            try:
                orders.append(schemas.ERPPurchaseOrder.model_validate(raw_order))
            except Exception as exc:  # pragma: no cover - Validierungsfehler
                LOGGER.warning("Ungültiger ERP-Auftrag übersprungen: %s", exc)
        return orders

    def import_purchase_orders(self, db, orders: list[schemas.ERPPurchaseOrder]) -> schemas.ERPImportResult:
        return crud.import_purchase_orders_from_payload(db, orders)

    async def sync_purchase_orders(self, db) -> schemas.ERPImportResult:
        orders = await self.fetch_purchase_orders()
        if not orders:
            return schemas.ERPImportResult(details=["Keine Bestellungen vom ERP erhalten."])
        return self.import_purchase_orders(db, orders)
