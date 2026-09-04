"""
Inventory service managing products, warehouses, distributors, stock levels, and safety thresholds.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.distributor import Distributor
from app.models.inventory import Inventory
from app.schemas.inventory_schema import (
    ProductCreate,
    ProductUpdate,
    WarehouseCreate,
    WarehouseUpdate,
    DistributorCreate,
    InventoryCreate,
    LowStockAlert,
)


# =====================================================================
# Product Operations
# =====================================================================
def create_product(db: Session, product_in: ProductCreate) -> Product:
    existing = db.query(Product).filter(Product.sku == product_in.sku).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with SKU '{product_in.sku}' already exists"
        )
    product = Product(**product_in.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_product(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()


def get_product_by_sku(db: Session, sku: str) -> Optional[Product]:
    return db.query(Product).filter(Product.sku == sku).first()


def get_products(db: Session, skip: int = 0, limit: int = 100) -> List[Product]:
    return db.query(Product).offset(skip).limit(limit).all()


def update_product(db: Session, product_id: int, product_update: ProductUpdate) -> Optional[Product]:
    product = get_product(db, product_id)
    if not product:
        return None
    update_data = product_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


# =====================================================================
# Warehouse Operations
# =====================================================================
def create_warehouse(db: Session, wh_in: WarehouseCreate) -> Warehouse:
    existing = db.query(Warehouse).filter(Warehouse.code == wh_in.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Warehouse with code '{wh_in.code}' already exists"
        )
    warehouse = Warehouse(**wh_in.model_dump())
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


def get_warehouse(db: Session, warehouse_id: int) -> Optional[Warehouse]:
    return db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()


def get_warehouses(db: Session, active_only: bool = False) -> List[Warehouse]:
    query = db.query(Warehouse)
    if active_only:
        query = query.filter(Warehouse.is_active.is_(True))
    return query.all()


def update_warehouse(db: Session, warehouse_id: int, wh_update: WarehouseUpdate) -> Optional[Warehouse]:
    warehouse = get_warehouse(db, warehouse_id)
    if not warehouse:
        return None
    update_data = wh_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(warehouse, field, value)
    db.commit()
    db.refresh(warehouse)
    return warehouse


# =====================================================================
# Distributor Operations
# =====================================================================
def create_distributor(db: Session, dist_in: DistributorCreate) -> Distributor:
    existing = db.query(Distributor).filter(Distributor.code == dist_in.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Distributor with code '{dist_in.code}' already exists"
        )
    distributor = Distributor(**dist_in.model_dump())
    db.add(distributor)
    db.commit()
    db.refresh(distributor)
    return distributor


def get_distributor(db: Session, distributor_id: int) -> Optional[Distributor]:
    return db.query(Distributor).filter(Distributor.id == distributor_id).first()


def get_distributors(db: Session, active_only: bool = False) -> List[Distributor]:
    query = db.query(Distributor)
    if active_only:
        query = query.filter(Distributor.is_active.is_(True))
    return query.all()


# =====================================================================
# Stock / Inventory Operations
# =====================================================================
def set_or_update_inventory(db: Session, inv_in: InventoryCreate) -> Inventory:
    # Ensure warehouse and product exist
    if not get_warehouse(db, inv_in.warehouse_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Warehouse with ID {inv_in.warehouse_id} not found"
        )
    if not get_product(db, inv_in.product_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {inv_in.product_id} not found"
        )

    inv = db.query(Inventory).filter(
        Inventory.warehouse_id == inv_in.warehouse_id,
        Inventory.product_id == inv_in.product_id
    ).first()

    if inv:
        inv.quantity = inv_in.quantity
        if inv_in.safety_stock is not None:
            inv.safety_stock = inv_in.safety_stock
        if inv_in.reorder_point is not None:
            inv.reorder_point = inv_in.reorder_point
        if inv_in.batch_number is not None:
            inv.batch_number = inv_in.batch_number
    else:
        inv = Inventory(**inv_in.model_dump())
        db.add(inv)

    db.commit()
    db.refresh(inv)
    return inv


def adjust_stock(db: Session, warehouse_id: int, product_id: int, delta: int) -> Inventory:
    inv = db.query(Inventory).filter(
        Inventory.warehouse_id == warehouse_id,
        Inventory.product_id == product_id
    ).first()

    if not inv:
        if delta < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot decrease stock for non-existent inventory record"
            )
        inv = Inventory(warehouse_id=warehouse_id, product_id=product_id, quantity=delta)
        db.add(inv)
    else:
        new_quantity = inv.quantity + delta
        if new_quantity < inv.reserved_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reduce stock to {new_quantity}: {inv.reserved_quantity} units are already reserved"
            )
        inv.quantity = new_quantity

    db.commit()
    db.refresh(inv)
    return inv


def reserve_stock(db: Session, warehouse_id: int, product_id: int, quantity: int) -> bool:
    inv = db.query(Inventory).filter(
        Inventory.warehouse_id == warehouse_id,
        Inventory.product_id == product_id
    ).first()

    if not inv or inv.available_quantity < quantity:
        return False

    inv.reserved_quantity += quantity
    db.commit()
    return True


def release_reserved_stock(db: Session, warehouse_id: int, product_id: int, quantity: int) -> bool:
    inv = db.query(Inventory).filter(
        Inventory.warehouse_id == warehouse_id,
        Inventory.product_id == product_id
    ).first()

    if not inv:
        return False

    inv.reserved_quantity = max(0, inv.reserved_quantity - quantity)
    db.commit()
    return True


def deduct_stock(db: Session, warehouse_id: int, product_id: int, quantity: int) -> bool:
    """Permanently deducts stock (both quantity and reserved quantity) upon shipment."""
    inv = db.query(Inventory).filter(
        Inventory.warehouse_id == warehouse_id,
        Inventory.product_id == product_id
    ).first()

    if not inv or inv.quantity < quantity:
        return False

    inv.quantity -= quantity
    inv.reserved_quantity = max(0, inv.reserved_quantity - quantity)
    db.commit()
    return True


def get_warehouse_stock(db: Session, warehouse_id: int) -> List[Inventory]:
    return db.query(Inventory).filter(Inventory.warehouse_id == warehouse_id).all()


def get_all_inventory(db: Session, skip: int = 0, limit: int = 100) -> List[Inventory]:
    return db.query(Inventory).offset(skip).limit(limit).all()


def get_stock_alerts(db: Session) -> List[LowStockAlert]:
    alerts = []
    inventories = db.query(Inventory).all()
    for inv in inventories:
        available = inv.available_quantity
        status_label = "OPTIMAL"
        if available <= inv.reorder_point:
            status_label = "CRITICAL"
        elif available <= inv.safety_stock:
            status_label = "LOW"

        if status_label in ("CRITICAL", "LOW"):
            suggested = max(inv.safety_stock * 2 - available, 10)
            alerts.append(
                LowStockAlert(
                    warehouse_id=inv.warehouse_id,
                    warehouse_name=inv.warehouse.name if inv.warehouse else f"Warehouse {inv.warehouse_id}",
                    product_id=inv.product_id,
                    product_name=inv.product.name if inv.product else f"Product {inv.product_id}",
                    sku=inv.product.sku if inv.product else "UNKNOWN",
                    current_quantity=inv.quantity,
                    safety_stock=inv.safety_stock,
                    reorder_point=inv.reorder_point,
                    status=status_label,
                    suggested_reorder_qty=suggested,
                )
            )
    return alerts
