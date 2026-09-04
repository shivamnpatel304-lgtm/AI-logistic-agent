"""
Pydantic schemas for Orders and Order Items
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.order import OrderStatus, OrderPriority


class OrderItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    unit_price: float
    allocated_warehouse_id: Optional[int] = None
    allocated_quantity: int = 0

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    distributor_id: int
    customer_name: str
    delivery_address: str
    delivery_latitude: float
    delivery_longitude: float
    priority: Optional[OrderPriority] = OrderPriority.NORMAL
    special_instructions: Optional[str] = None


class OrderCreate(OrderBase):
    items: List[OrderItemCreate] = Field(..., min_length=1, description="Order must contain at least one item")


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    priority: Optional[OrderPriority] = None
    special_instructions: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderResponse(OrderBase):
    id: int
    order_number: str
    status: OrderStatus
    total_amount: float
    total_weight_kg: float
    ai_analysis_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True


class OrderAgentAnalysis(BaseModel):
    order_id: int
    order_number: str
    is_valid: bool
    recommended_priority: str
    estimated_total_weight_kg: float
    estimated_total_volume_m3: float
    cold_chain_required: bool
    anomalies_detected: List[str] = []
    fulfillment_risk_score: float = Field(..., description="Risk score from 0.0 (low) to 1.0 (high)")
    ai_recommendation: str
