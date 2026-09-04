"""
API routes for Warehouse Order Allocation and Optimization.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.allocation_schema import (
    OrderAllocationResult,
    AllocationSimulateRequest,
)
from app.agents import allocation_agent

router = APIRouter(prefix="/allocation", tags=["Allocation & Fulfillment"])


@router.post("/simulate", response_model=OrderAllocationResult)
def simulate_order_allocation(
    request: AllocationSimulateRequest,
    db: Session = Depends(get_db),
):
    """
    Simulates intelligent order fulfillment without locking or reserving warehouse stock.
    Evaluates closest warehouses and single-vs-multi warehouse tradeoffs.
    """
    return allocation_agent.optimize_order_fulfillment(
        db=db,
        order_id=request.order_id,
        max_radius_km=request.max_radius_km or 500.0,
        prefer_single_warehouse=request.prefer_single_warehouse if request.prefer_single_warehouse is not None else True,
        execute_allocation=False,
    )


@router.post("/allocate/{order_id}", response_model=OrderAllocationResult)
def execute_order_allocation(
    order_id: int,
    max_radius_km: float = Query(500.0, ge=10.0, le=5000.0),
    prefer_single_warehouse: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Executes AI-optimized fulfillment: assigns warehouse sources to order items
    and reserves stock across the warehouse network.
    """
    return allocation_agent.optimize_order_fulfillment(
        db=db,
        order_id=order_id,
        max_radius_km=max_radius_km,
        prefer_single_warehouse=prefer_single_warehouse,
        execute_allocation=True,
    )
