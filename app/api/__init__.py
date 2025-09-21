"""API-Router für das Lagerverwaltungssystem."""

from fastapi import APIRouter

from . import erp, inventory, items, locations, purchase_orders, suppliers

api_router = APIRouter()
api_router.include_router(items.router, prefix="/items", tags=["Artikel"])
api_router.include_router(locations.router, prefix="/locations", tags=["Lagerorte"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["Lieferanten"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["Bestände"])
api_router.include_router(purchase_orders.router, prefix="/purchase-orders", tags=["Bestellungen"])
api_router.include_router(erp.router, prefix="/erp", tags=["ERP"])

__all__ = ["api_router"]
