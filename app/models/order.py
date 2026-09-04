"""
Order and OrderItem database models
"""
from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    ALLOCATED = "ALLOCATED"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class OrderPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(64), unique=True, index=True, nullable=False)
    distributor_id = Column(Integer, ForeignKey("distributors.id"), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    delivery_address = Column(String(500), nullable=False)
    delivery_latitude = Column(Float, nullable=False)
    delivery_longitude = Column(Float, nullable=False)
    status = Column(String(50), default=OrderStatus.PENDING.value, index=True)
    priority = Column(String(50), default=OrderPriority.NORMAL.value)
    total_amount = Column(Float, default=0.0)
    total_weight_kg = Column(Float, default=0.0)
    special_instructions = Column(Text, nullable=True)
    ai_analysis_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    distributor = relationship("Distributor", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False, default=0.0)
    allocated_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    allocated_quantity = Column(Integer, default=0)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    allocated_warehouse = relationship("Warehouse")
