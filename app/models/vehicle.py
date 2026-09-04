"""
Vehicle / Fleet database model
"""
from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database.connection import Base


class VehicleType(str, enum.Enum):
    VAN = "VAN"
    TRUCK = "TRUCK"
    REEFER = "REEFER"  # Refrigerated vehicle for cold-chain / perishable


class VehicleStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    IN_TRANSIT = "IN_TRANSIT"
    MAINTENANCE = "MAINTENANCE"


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(50), unique=True, index=True, nullable=False)
    vehicle_type = Column(String(50), default=VehicleType.VAN.value)
    max_weight_capacity_kg = Column(Float, nullable=False, default=1500.0)
    max_volume_capacity_m3 = Column(Float, nullable=False, default=15.0)
    current_status = Column(String(50), default=VehicleStatus.AVAILABLE.value)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True, index=True)
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    warehouse = relationship("Warehouse", back_populates="vehicles")
