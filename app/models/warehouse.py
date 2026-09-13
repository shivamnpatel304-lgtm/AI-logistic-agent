"""
Warehouse database model.
Applies:
- Inheritance: Inherits common columns and behaviors from BaseEntity.
- Encapsulation: Encapsulates capacity calculations and spatial coordinates.
"""
from sqlalchemy import Column, String, Float, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseEntity


class Warehouse(BaseEntity):
    __tablename__ = "warehouses"

    code = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    capacity_m3 = Column(Float, default=1000.0)
    current_utilization = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)

    # Relationships
    inventory_records = relationship("Inventory", back_populates="warehouse", cascade="all, delete-orphan")
    vehicles = relationship("Vehicle", back_populates="warehouse")

    @property
    def available_capacity_m3(self) -> float:
        """Encapsulated calculation of remaining volume capacity."""
        return max(0.0, round(self.capacity_m3 - self.current_utilization, 2))

    @property
    def utilization_percentage(self) -> float:
        """Encapsulated calculation of current utilization rate."""
        if self.capacity_m3 <= 0:
            return 100.0
        return round((self.current_utilization / self.capacity_m3) * 100.0, 1)

    def can_accommodate_volume(self, volume_m3: float) -> bool:
        """Encapsulates volume threshold validation."""
        active = self.is_active if self.is_active is not None else True
        return bool(active and (self.available_capacity_m3 >= volume_m3))

    def record_utilization(self, delta_volume_m3: float) -> None:
        """Safely modifies warehouse volumetric utilization."""
        new_val = self.current_utilization + delta_volume_m3
        self.current_utilization = max(0.0, round(new_val, 3))

    def __repr__(self) -> str:
        return f"<Warehouse(code='{self.code}', name='{self.name}')>"
