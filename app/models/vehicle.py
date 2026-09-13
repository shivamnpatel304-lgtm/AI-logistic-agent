"""
Vehicle / Fleet database model.
Applies:
- Inheritance: Inherits common columns and behaviors from BaseEntity.
- Encapsulation: Encapsulates payload capacity verification and fleet status state transitions.
"""
import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseEntity


class VehicleType(str, enum.Enum):
    VAN = "VAN"
    TRUCK = "TRUCK"
    REEFER = "REEFER"  # Refrigerated vehicle for cold-chain / perishable cargo


class VehicleStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    IN_TRANSIT = "IN_TRANSIT"
    MAINTENANCE = "MAINTENANCE"


class Vehicle(BaseEntity):
    __tablename__ = "vehicles"

    plate_number = Column(String(50), unique=True, index=True, nullable=False)
    vehicle_type = Column(String(50), default=VehicleType.VAN.value)
    max_weight_capacity_kg = Column(Float, nullable=False, default=1500.0)
    max_volume_capacity_m3 = Column(Float, nullable=False, default=15.0)
    current_status = Column(String(50), default=VehicleStatus.AVAILABLE.value)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True, index=True)
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)

    # Relationships
    warehouse = relationship("Warehouse", back_populates="vehicles")

    # =========================================================================
    # Encapsulated Domain Properties
    # =========================================================================
    @property
    def is_available(self) -> bool:
        return self.current_status == VehicleStatus.AVAILABLE.value

    @property
    def is_reefer(self) -> bool:
        return self.vehicle_type == VehicleType.REEFER.value

    # =========================================================================
    # Encapsulated Business Rules & State Transitions
    # =========================================================================
    def can_accommodate(self, weight_kg: float, volume_m3: float, requires_reefer: bool = False) -> bool:
        """
        Validates if vehicle meets load and environmental compliance.
        """
        if requires_reefer and not self.is_reefer:
            return False
        if weight_kg > self.max_weight_capacity_kg:
            return False
        if volume_m3 > self.max_volume_capacity_m3:
            return False
        return True

    def assign(self) -> None:
        """Transitions vehicle to assigned status."""
        if not self.is_available:
            raise ValueError(f"Vehicle {self.plate_number} is not available (Current: {self.current_status}).")
        self.current_status = VehicleStatus.ASSIGNED.value

    def mark_in_transit(self) -> None:
        """Transitions vehicle to in-transit status upon departure."""
        self.current_status = VehicleStatus.IN_TRANSIT.value

    def release(self) -> None:
        """Releases vehicle back to available pool upon delivery completion."""
        self.current_status = VehicleStatus.AVAILABLE.value

    def mark_maintenance(self) -> None:
        """Marks vehicle for maintenance."""
        self.current_status = VehicleStatus.MAINTENANCE.value

    def __repr__(self) -> str:
        return f"<Vehicle(plate='{self.plate_number}', type='{self.vehicle_type}', status='{self.current_status}')>"
