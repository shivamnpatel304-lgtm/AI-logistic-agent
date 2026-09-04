"""
Routes module initialization
Exports all individual routers.
"""
from app.api.routes.order_routes import router as order_router
from app.api.routes.inventory_routes import router as inventory_router
from app.api.routes.allocation_routes import router as allocation_router
from app.api.routes.logistics_routes import router as logistics_router

__all__ = [
    "order_router",
    "inventory_router",
    "allocation_router",
    "logistics_router",
]
