"""
Product database model
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database.connection import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="General")
    unit_price = Column(Float, nullable=False, default=0.0)
    weight_kg = Column(Float, nullable=False, default=1.0)
    volume_m3 = Column(Float, nullable=False, default=0.01)
    is_perishable = Column(Boolean, default=False)
    requires_cold_chain = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    inventory_items = relationship("Inventory", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")
