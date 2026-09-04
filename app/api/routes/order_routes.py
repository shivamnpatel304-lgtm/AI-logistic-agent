"""
API routes for Order management and AI Order Agent assessment.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.order_schema import (
    OrderCreate,
    OrderResponse,
    OrderUpdate,
    OrderAgentAnalysis,
)
from app.services import order_service
from app.agents import order_agent

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_new_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    """Create a new sales/distribution order."""
    return order_service.create_order(db=db, order_in=order_in)


@router.get("/", response_model=List[OrderResponse])
def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by OrderStatus"),
    db: Session = Depends(get_db),
):
    """Retrieve orders with optional pagination and status filtering."""
    return order_service.get_orders(db=db, skip=skip, limit=limit, status_filter=status)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_details(order_id: int, db: Session = Depends(get_db)):
    """Fetch complete details for a specific order."""
    order = order_service.get_order(db=db, order_id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
        )
    return order


@router.patch("/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, order_update: OrderUpdate, db: Session = Depends(get_db)):
    """Update order status, priority, or instructions."""
    order = order_service.update_order(db=db, order_id=order_id, order_update=order_update)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
        )
    return order


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    """Cancel an active order and release any reserved inventory."""
    order = order_service.cancel_order(db=db, order_id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
        )
    return order


@router.post("/{order_id}/analyze", response_model=OrderAgentAnalysis)
def analyze_order_with_agent(order_id: int, db: Session = Depends(get_db)):
    """Trigger AI Order Agent to evaluate order risks, priority, cold chain, and anomalies."""
    order = order_service.get_order(db=db, order_id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
        )
    return order_agent.analyze_order(db=db, order=order)
