"""
Logistics, Fleet, and Dispatch Service.
Applies:
- Inheritance: Subclasses BaseService[Vehicle].
- Encapsulation: Encapsulates vehicle matching, cargo constraints, route ETAs, and dispatch state transitions.
- Zero Regressions: Preserves top-level function interfaces for backward compatibility.
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
from app.services.base_service import BaseService
from app.services.allocation_strategies import DistanceCalculator
from app.services.inventory_service import deduct_stock


class LogisticsService(BaseService[Vehicle]):
    def __init__(self):
        super().__init__(Vehicle)

    def register_vehicle(self, db: Session, vehicle_in: VehicleCreate) -> Vehicle:
        existing = db.query(Vehicle).filter(Vehicle.plate_number == vehicle_in.plate_number).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vehicle with plate number '{vehicle_in.plate_number}' already exists",
            )
        vehicle = Vehicle(**vehicle_in.model_dump())
        return self.save(db, vehicle)

    def list_vehicles(self, db: Session, status_filter: Optional[str] = None) -> List[Vehicle]:
        query = db.query(Vehicle)
        if status_filter:
            query = query.filter(Vehicle.current_status == status_filter.upper())
        return query.all()

    def update_status(self, db: Session, vehicle_id: int, new_status: VehicleStatus) -> Optional[Vehicle]:
        vehicle = self.get_by_id(db, vehicle_id)
        if not vehicle:
            return None
        vehicle.current_status = new_status.value
        db.commit()
        db.refresh(vehicle)
        return vehicle

    def plan_dispatch(self, db: Session, order_id: int) -> DispatchRecommendation:
        """
        Evaluates order requirements (weight, volume, refrigeration) and recommends the best vehicle and route.
        """
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {order_id} not found",
            )

        # Determine fulfillment warehouse
        warehouse_id = None
        for item in order.items or []:
            if item.allocated_warehouse_id:
                warehouse_id = item.allocated_warehouse_id
                break

        if not warehouse_id:
            wh = db.query(Warehouse).filter(Warehouse.is_active.is_(True)).first()
            if not wh:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No warehouse found for dispatch planning",
                )
            warehouse_id = wh.id

        warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()

        # Calculate cargo metrics
        total_weight = 0.0
        total_volume = 0.0
        requires_reefer = False

        for item in order.items or []:
            if item.product:
                total_weight += item.product.weight_kg * item.quantity
                total_volume += item.product.volume_m3 * item.quantity
                if item.product.is_temperature_controlled:
                    requires_reefer = True

        distance_km = DistanceCalculator.calculate(
            warehouse.latitude,
            warehouse.longitude,
            order.delivery_latitude,
            order.delivery_longitude,
        )
        transit_hours = round((distance_km / 50.0) + 0.5, 2)

        # Vehicle matching using encapsulated can_accommodate method
        vehicles = (
            db.query(Vehicle)
            .filter(
                Vehicle.current_status == VehicleStatus.AVAILABLE.value,
                Vehicle.warehouse_id == warehouse.id,
            )
            .all()
        )

        assigned_vehicle: Optional[Vehicle] = None
        if requires_reefer:
            assigned_vehicle = next((v for v in vehicles if v.is_reefer and v.can_accommodate(total_weight, total_volume, requires_reefer=True)), None)

        if not assigned_vehicle:
            suitable = [
                v for v in vehicles
                if v.can_accommodate(total_weight, total_volume, requires_reefer=requires_reefer)
            ]
            if suitable:
                assigned_vehicle = suitable[0]

        dispatch_notes = []
        if requires_reefer and (not assigned_vehicle or not assigned_vehicle.is_reefer):
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

    def execute_dispatch(self, db: Session, request: DispatchRequest) -> Order:
        """
        Finalizes order dispatch: changes status, commits vehicle assignment, and deducts inventory.
        """
        order = db.query(Order).filter(Order.id == request.order_id).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {request.order_id} not found",
            )

        if not order.can_transition_to(OrderStatus.DISPATCHED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot dispatch order in '{order.status}' status",
            )

        # Vehicle assignment
        if request.vehicle_id:
            vehicle = self.get_by_id(db, request.vehicle_id)
            if vehicle:
                vehicle.mark_in_transit()

        # Deduct allocated warehouse inventory
        for item in order.items or []:
            wh_id = item.allocated_warehouse_id or request.warehouse_id
            if wh_id:
                deduct_stock(db, wh_id, item.product_id, item.quantity)

        order.transition_to(OrderStatus.DISPATCHED)
        db.commit()
        db.refresh(order)
        return order


# Singleton instance
logistics_service = LogisticsService()


# =============================================================================
# Functional Facade (Backward Compatibility)
# =============================================================================
def create_vehicle(db: Session, vehicle_in: VehicleCreate) -> Vehicle:
    return logistics_service.register_vehicle(db, vehicle_in)


def get_vehicles(db: Session, status_filter: Optional[str] = None) -> List[Vehicle]:
    return logistics_service.list_vehicles(db, status_filter=status_filter)


def get_vehicle(db: Session, vehicle_id: int) -> Optional[Vehicle]:
    return logistics_service.get_by_id(db, vehicle_id)


def update_vehicle_status(db: Session, vehicle_id: int, new_status: VehicleStatus) -> Optional[Vehicle]:
    return logistics_service.update_status(db, vehicle_id, new_status)


def plan_dispatch(db: Session, order_id: int) -> DispatchRecommendation:
    return logistics_service.plan_dispatch(db, order_id)


def execute_dispatch(db: Session, request: DispatchRequest) -> Order:
    return logistics_service.execute_dispatch(db, request)
