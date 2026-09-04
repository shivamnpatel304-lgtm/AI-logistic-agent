"""
API routes for Products, Warehouses, Distributors, and Inventory Management.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.inventory_schema import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseResponse,
    DistributorCreate,
    DistributorResponse,
    InventoryCreate,
    InventoryResponse,
    StockAdjustmentRequest,
    LowStockAlert,
    RebalanceRecommendation,
)
from app.services import inventory_service, allocation_service
from app.agents import inventory_agent

router = APIRouter(prefix="/inventory", tags=["Inventory & Products"])


# =====================================================================
# Products
# =====================================================================
@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product SKU in the catalog."""
    return inventory_service.create_product(db=db, product_in=product_in)


@router.get("/products", response_model=List[ProductResponse])
def list_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all registered products."""
    return inventory_service.get_products(db=db, skip=skip, limit=limit)


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Retrieve product details by ID."""
    product = inventory_service.get_product(db=db, product_id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    return product


# =====================================================================
# Warehouses
# =====================================================================
@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(wh_in: WarehouseCreate, db: Session = Depends(get_db)):
    """Register a new fulfillment center / warehouse."""
    return inventory_service.create_warehouse(db=db, wh_in=wh_in)


@router.get("/warehouses", response_model=List[WarehouseResponse])
def list_warehouses(active_only: bool = False, db: Session = Depends(get_db)):
    """List all regional warehouses."""
    return inventory_service.get_warehouses(db=db, active_only=active_only)


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def get_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    """Get warehouse details by ID."""
    warehouse = inventory_service.get_warehouse(db=db, warehouse_id=warehouse_id)
    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Warehouse with ID {warehouse_id} not found"
        )
    return warehouse


# =====================================================================
# Distributors
# =====================================================================
@router.post("/distributors", response_model=DistributorResponse, status_code=status.HTTP_201_CREATED)
def create_distributor(dist_in: DistributorCreate, db: Session = Depends(get_db)):
    """Create a client/distributor profile."""
    return inventory_service.create_distributor(db=db, dist_in=dist_in)


@router.get("/distributors", response_model=List[DistributorResponse])
def list_distributors(active_only: bool = False, db: Session = Depends(get_db)):
    """List all distributors."""
    return inventory_service.get_distributors(db=db, active_only=active_only)


# =====================================================================
# Stock & Alerts
# =====================================================================
@router.post("/stock", response_model=InventoryResponse)
def set_or_update_stock(inv_in: InventoryCreate, db: Session = Depends(get_db)):
    """Set absolute stock quantity or thresholds for a warehouse-product pair."""
    return inventory_service.set_or_update_inventory(db=db, inv_in=inv_in)


@router.post("/stock/adjust", response_model=InventoryResponse)
def adjust_stock(request: StockAdjustmentRequest, db: Session = Depends(get_db)):
    """Increment or decrement inventory stock quantity."""
    return inventory_service.adjust_stock(
        db=db,
        warehouse_id=request.warehouse_id,
        product_id=request.product_id,
        delta=request.quantity_delta,
    )


@router.get("/stock", response_model=List[InventoryResponse])
def list_all_stock(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List inventory across all warehouses."""
    return inventory_service.get_all_inventory(db=db, skip=skip, limit=limit)


@router.get("/stock/warehouse/{warehouse_id}", response_model=List[InventoryResponse])
def get_warehouse_stock(warehouse_id: int, db: Session = Depends(get_db)):
    """Retrieve stock levels for a specific warehouse."""
    return inventory_service.get_warehouse_stock(db=db, warehouse_id=warehouse_id)


@router.get("/alerts", response_model=List[LowStockAlert])
def get_stock_alerts(db: Session = Depends(get_db)):
    """Retrieve items at or below safety stock / reorder thresholds."""
    return inventory_service.get_stock_alerts(db=db)


@router.get("/health", response_model=Dict[str, Any])
def get_inventory_network_health(db: Session = Depends(get_db)):
    """Run AI Inventory Agent health assessment on global inventory."""
    return inventory_agent.assess_network_health(db=db)


@router.get("/rebalance-recommendations", response_model=List[RebalanceRecommendation])
def get_rebalance_recommendations(db: Session = Depends(get_db)):
    """Generate inter-warehouse rebalance recommendations."""
    return allocation_service.generate_rebalance_recommendations(db=db)
