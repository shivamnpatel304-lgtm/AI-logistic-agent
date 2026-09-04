"""
Pydantic schemas for Allocation, Dispatch, and Logistics Management
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.vehicle import VehicleType, VehicleStatus


# Vehicle Schemas
class VehicleBase(BaseModel):
    plate_number: str
    vehicle_type: Optional[VehicleType] = VehicleType.VAN
    max_weight_capacity_kg: float = Field(..., gt=0)
    max_volume_capacity_m3: float = Field(..., gt=0)
    current_status: Optional[VehicleStatus] = VehicleStatus.AVAILABLE
    warehouse_id: Optional[int] = None
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    vehicle_type: Optional[VehicleType] = None
    max_weight_capacity_kg: Optional[float] = None
    max_volume_capacity_m3: Optional[float] = None
    current_status: Optional[VehicleStatus] = None
    warehouse_id: Optional[int] = None
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None


class VehicleResponse(VehicleBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Allocation Schemas
class ItemAllocationDetail(BaseModel):
    product_id: int
    product_name: str
    requested_quantity: int
    allocated_quantity: int
    unfulfilled_quantity: int
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    distance_km: Optional[float] = None


class OrderAllocationResult(BaseModel):
    order_id: int
    order_number: str
    is_fully_allocated: bool
    total_items_requested: int
    total_items_allocated: int
    allocations: List[ItemAllocationDetail]
    fulfillment_centers: List[str]
    optimization_notes: str


class AllocationSimulateRequest(BaseModel):
    order_id: int
    max_radius_km: Optional[float] = 500.0
    prefer_single_warehouse: Optional[bool] = True


class DispatchRecommendation(BaseModel):
    order_id: int
    warehouse_id: int
    warehouse_name: str
    assigned_vehicle_id: Optional[int] = None
    vehicle_plate: Optional[str] = None
    vehicle_type: Optional[str] = None
    total_weight_kg: float
    total_volume_m3: float
    estimated_distance_km: float
    estimated_transit_hours: float
    requires_reefer: bool
    status: str
    dispatch_notes: str


class DispatchRequest(BaseModel):
    order_id: int
    warehouse_id: Optional[int] = None
    vehicle_id: Optional[int] = None
