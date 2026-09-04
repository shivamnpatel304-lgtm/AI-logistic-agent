"""
API routes for Vehicle fleet management, dispatch planning, and execution.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.allocation_schema import (
    VehicleCreate,
    VehicleResponse,
    VehicleUpdate,
    DispatchRecommendation,
    DispatchRequest,
)
from app.schemas.order_schema import OrderResponse
from app.models.vehicle import VehicleStatus
from app.services import logistics_service
from app.agents import logistics_agent

router = APIRouter(prefix="/logistics", tags=["Logistics & Fleet"])


@router.post("/vehicles", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def register_vehicle(vehicle_in: VehicleCreate, db: Session = Depends(get_db)):
    """Register a new vehicle into the fleet."""
    return logistics_service.create_vehicle(db=db, vehicle_in=vehicle_in)


@router.get("/vehicles", response_model=List[VehicleResponse])
def list_vehicles(
    status: Optional[str] = Query(None, description="Filter by VehicleStatus"),
    db: Session = Depends(get_db),
):
    """List fleet vehicles with optional status filter."""
    return logistics_service.get_vehicles(db=db, status_filter=status)


@router.get("/vehicles/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle_details(vehicle_id: int, db: Session = Depends(get_db)):
    """Get vehicle information by ID."""
    vehicle = logistics_service.get_vehicle(db=db, vehicle_id=vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {vehicle_id} not found"
        )
    return vehicle


@router.patch("/vehicles/{vehicle_id}/status", response_model=VehicleResponse)
def update_status(vehicle_id: int, new_status: VehicleStatus, db: Session = Depends(get_db)):
    """Update vehicle operational status."""
    vehicle = logistics_service.update_vehicle_status(db=db, vehicle_id=vehicle_id, new_status=new_status)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID {vehicle_id} not found"
        )
    return vehicle


@router.get("/plan-dispatch/{order_id}", response_model=DispatchRecommendation)
def plan_order_dispatch(order_id: int, db: Session = Depends(get_db)):
    """
    AI Logistics Agent evaluates order requirements (cold-chain, weight, volume)
    and matches the best available fleet vehicle and calculates route ETA.
    """
    return logistics_agent.evaluate_and_plan_dispatch(db=db, order_id=order_id)


@router.post("/dispatch", response_model=OrderResponse)
def execute_order_dispatch(request: DispatchRequest, db: Session = Depends(get_db)):
    """
    Finalizes order dispatch: updates order status, assigns vehicle, and deducts inventory.
    """
    return logistics_agent.dispatch_order(db=db, request=request)
