"""
Product database model.
Applies:
- Inheritance: Inherits common columns and behaviors from BaseEntity.
- Encapsulation: Encapsulates dimensional calculations and cold chain requirements.
"""
from sqlalchemy import Column, String, Float, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseEntity


class Product(BaseEntity):
    __tablename__ = "products"

    sku = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="General")
    unit_price = Column(Float, nullable=False, default=0.0)
    weight_kg = Column(Float, nullable=False, default=1.0)
    volume_m3 = Column(Float, nullable=False, default=0.01)
    is_perishable = Column(Boolean, default=False)
    requires_cold_chain = Column(Boolean, default=False)

    # Relationships
    inventory_items = relationship("Inventory", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")

    @property
    def is_temperature_controlled(self) -> bool:
        """Encapsulated check for temperature regulation requirements."""
        return bool(self.is_perishable or self.requires_cold_chain)

    def compute_bulk_metrics(self, quantity: int) -> dict:
        """
        Encapsulates calculations of combined weight, volume, and total price for a given batch.
        """
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
        return {
            "total_weight_kg": round(self.weight_kg * quantity, 3),
            "total_volume_m3": round(self.volume_m3 * quantity, 4),
            "total_price": round(self.unit_price * quantity, 2),
            "requires_reefer": self.is_temperature_controlled,
        }

    def __repr__(self) -> str:
        return f"<Product(sku='{self.sku}', name='{self.name}')>"
