"""
Logistics service managing vehicle fleet, capacity planning, dispatch planning, and route ETA.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.order import Order, OrderStatus
from app.models.vehicle import Vehicle, VehicleType, VehicleStatus
from app.models.warehouse import Warehouse
from app.schemas.allocation_schema import (
    VehicleCreate,
    VehicleUpdate,
    DispatchRecommendation,
    DispatchRequest,
)
from app.services.allocation_service import calculate_distance_km
from app.services.inventory_service import deduct_stock


def create_vehicle(db: Session, vehicle_in: VehicleCreate) -> Vehicle:
    existing = db.query(Vehicle).filter(Vehicle.plate_number == vehicle_in.plate_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vehicle with plate number '{vehicle_in.plate_number}' already exists"
        )
    vehicle = Vehicle(**vehicle_in.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def get_vehicles(db: Session, status_filter: Optional[str] = None) -> List[Vehicle]:
    query = db.query(Vehicle)
    if status_filter:
        query = query.filter(Vehicle.current_status == status_filter.upper())
    return query.all()


def get_vehicle(db: Session, vehicle_id: int) -> Optional[Vehicle]:
    return db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()


def update_vehicle_status(db: Session, vehicle_id: int, new_status: VehicleStatus) -> Optional[Vehicle]:
    vehicle = get_vehicle(db, vehicle_id)
    if not vehicle:
        return None
    vehicle.current_status = new_status.value
    db.commit()
    db.refresh(vehicle)
    return vehicle


def plan_dispatch(db: Session, order_id: int) -> DispatchRecommendation:
    """
    Evaluates order requirements (weight, volume, refrigeration) and recommends the best vehicle and route.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found"
        )

    # Determine warehouse (use allocated warehouse of first item or primary)
    warehouse_id = None
    for item in order.items:
        if item.allocated_warehouse_id:
            warehouse_id = item.allocated_warehouse_id
            break

    if not warehouse_id:
        # Fallback to closest active warehouse
        wh = db.query(Warehouse).filter(Warehouse.is_active.is_(True)).first()
        if not wh:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No warehouse found for dispatch planning"
            )
        warehouse_id = wh.id

    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()

    # Calculate total weight and volume, check refrigeration requirements
    total_weight = 0.0
    total_volume = 0.0
    requires_reefer = False

    for item in order.items:
        if item.product:
            total_weight += item.product.weight_kg * item.quantity
            total_volume += item.product.volume_m3 * item.quantity
            if item.product.is_perishable or item.product.requires_cold_chain:
                requires_reefer = True

    # Calculate distance and transit hours
    distance_km = calculate_distance_km(
        warehouse.latitude,
        warehouse.longitude,
        order.delivery_latitude,
        order.delivery_longitude
    )
    # Average logistics speed 50 km/h + 0.5 hour handling buffer
    transit_hours = round((distance_km / 50.0) + 0.5, 2)

    # Find suitable available vehicle
    vehicles = db.query(Vehicle).filter(
        Vehicle.current_status == VehicleStatus.AVAILABLE.value,
        Vehicle.warehouse_id == warehouse.id,
    ).all()

    assigned_vehicle = None
    if requires_reefer:
        assigned_vehicle = next((v for v in vehicles if v.vehicle_type == VehicleType.REEFER.value), None)

    if not assigned_vehicle:
        # Sort vehicles by capacity
        suitable = [
            v for v in vehicles
            if v.max_weight_capacity_kg >= total_weight and v.max_volume_capacity_m3 >= total_volume
        ]
        if suitable:
            assigned_vehicle = suitable[0]

    dispatch_notes = []
    if requires_reefer and (not assigned_vehicle or assigned_vehicle.vehicle_type != VehicleType.REEFER.value):
        dispatch_notes.append("WARNING: Cold-chain items present but no dedicated Reefer vehicle available.")
    if not assigned_vehicle:
        dispatch_notes.append("No currently available vehicle at warehouse matching load capacity; external fleet dispatch recommended.")
    else:
        dispatch_notes.append(f"Vehicle {assigned_vehicle.plate_number} ({assigned_vehicle.vehicle_type}) assigned.")

    return DispatchRecommendation(
        order_id=order.id,
        warehouse_id=warehouse.id,
        warehouse_name=warehouse.name,
        assigned_vehicle_id=assigned_vehicle.id if assigned_vehicle else None,
        vehicle_plate=assigned_vehicle.plate_number if assigned_vehicle else None,
        vehicle_type=assigned_vehicle.vehicle_type if assigned_vehicle else None,
        total_weight_kg=round(total_weight, 2),
        total_volume_m3=round(total_volume, 3),
        estimated_distance_km=distance_km,
        estimated_transit_hours=transit_hours,
        requires_reefer=requires_reefer,
        status="READY_FOR_DISPATCH" if assigned_vehicle else "PENDING_VEHICLE",
        dispatch_notes=" ".join(dispatch_notes),
    )


def execute_dispatch(db: Session, request: DispatchRequest) -> Order:
    """
    Finalizes order dispatch: changes status, commits vehicle assignment, and deducts inventory.
    """
    order = db.query(Order).filter(Order.id == request.order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {request.order_id} not found"
        )

    if order.status in (OrderStatus.DISPATCHED.value, OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot dispatch order in '{order.status}' status"
        )

    # Assign vehicle if provided
    if request.vehicle_id:
        vehicle = get_vehicle(db, request.vehicle_id)
        if vehicle:
            vehicle.current_status = VehicleStatus.IN_TRANSIT.value

    # Deduct stock for all order items from their allocated warehouse
    for item in order.items:
        wh_id = item.allocated_warehouse_id or request.warehouse_id
        if wh_id:
            deduct_stock(db, wh_id, item.product_id, item.quantity)

    order.status = OrderStatus.DISPATCHED.value
    db.commit()
    db.refresh(order)
    return order
