"""
Services module initialization
"""
from app.services import (
    order_service,
    inventory_service,
    allocation_service,
    logistics_service,
)

__all__ = [
    "order_service",
    "inventory_service",
    "allocation_service",
    "logistics_service",
]
