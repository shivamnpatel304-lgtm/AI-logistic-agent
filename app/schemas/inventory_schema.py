"""
Pydantic schemas for Inventory, Products, Warehouses, and Distributors
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# Product Schemas
class ProductBase(BaseModel):
    sku: str
    name: str
    category: Optional[str] = "General"
    unit_price: float = Field(..., ge=0)
    weight_kg: float = Field(..., gt=0)
    volume_m3: float = Field(..., gt=0)
    is_perishable: Optional[bool] = False
    requires_cold_chain: Optional[bool] = False


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[float] = None
    weight_kg: Optional[float] = None
    volume_m3: Optional[float] = None
    is_perishable: Optional[bool] = None
    requires_cold_chain: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Warehouse Schemas
class WarehouseBase(BaseModel):
    code: str
    name: str
    address: str
    city: Optional[str] = None
    latitude: float
    longitude: float
    capacity_m3: Optional[float] = 1000.0
    is_active: Optional[bool] = True


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity_m3: Optional[float] = None
    is_active: Optional[bool] = None


class WarehouseResponse(WarehouseBase):
    id: int
    current_utilization: float
    created_at: datetime

    class Config:
        from_attributes = True


# Distributor Schemas
class DistributorBase(BaseModel):
    code: str
    name: str
    contact_email: str
    phone: Optional[str] = None
    address: str
    latitude: float
    longitude: float
    tier: Optional[str] = "Standard"
    is_active: Optional[bool] = True


class DistributorCreate(DistributorBase):
    pass


class DistributorResponse(DistributorBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Inventory Schemas
class InventoryBase(BaseModel):
    warehouse_id: int
    product_id: int
    quantity: int = Field(..., ge=0)
    safety_stock: Optional[int] = 20
    reorder_point: Optional[int] = 10
    batch_number: Optional[str] = None


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    quantity: Optional[int] = None
    reserved_quantity: Optional[int] = None
    safety_stock: Optional[int] = None
    reorder_point: Optional[int] = None
    batch_number: Optional[str] = None


class InventoryResponse(InventoryBase):
    id: int
    reserved_quantity: int
    available_quantity: int
    updated_at: datetime
    product: Optional[ProductResponse] = None
    warehouse: Optional[WarehouseResponse] = None

    class Config:
        from_attributes = True


class StockAdjustmentRequest(BaseModel):
    warehouse_id: int
    product_id: int
    quantity_delta: int = Field(..., description="Positive to add stock, negative to reduce stock")
    reason: Optional[str] = "Manual adjustment"


class LowStockAlert(BaseModel):
    warehouse_id: int
    warehouse_name: str
    product_id: int
    product_name: str
    sku: str
    current_quantity: int
    safety_stock: int
    reorder_point: int
    status: str  # "CRITICAL", "LOW", "OPTIMAL"
    suggested_reorder_qty: int


class RebalanceRecommendation(BaseModel):
    product_id: int
    product_name: str
    source_warehouse_id: int
    source_warehouse_name: str
    target_warehouse_id: int
    target_warehouse_name: str
    recommended_transfer_quantity: int
    reason: str
