"""
Models module initialization
Exports all SQLAlchemy models for clean imports and Base registration.
"""
from app.database.connection import Base
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.distributor import Distributor
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem, OrderStatus, OrderPriority
from app.models.vehicle import Vehicle, VehicleType, VehicleStatus

__all__ = [
    "Base",
    "Product",
    "Warehouse",
    "Distributor",
    "Inventory",
    "Order",
    "OrderItem",
    "OrderStatus",
    "OrderPriority",
    "Vehicle",
    "VehicleType",
    "VehicleStatus",
]
