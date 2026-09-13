"""
Inventory, Product, Warehouse, and Distributor Services.
Applies:
- Inheritance: Subclasses BaseService[T] for ProductService, WarehouseService, DistributorService, InventoryService.
- Encapsulation: Encapsulates stock validation, reserves, release, and threshold alert calculations.
- Zero Regressions: Preserves all top-level function interfaces for full backward compatibility.
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
from app.services.base_service import BaseService


class ProductService(BaseService[Product]):
    def __init__(self):
        super().__init__(Product)

    def create(self, db: Session, product_in: ProductCreate) -> Product:
        existing = db.query(Product).filter(Product.sku == product_in.sku).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with SKU '{product_in.sku}' already exists",
            )
        product = Product(**product_in.model_dump())
        return self.save(db, product)

    def get_by_sku(self, db: Session, sku: str) -> Optional[Product]:
        return db.query(Product).filter(Product.sku == sku).first()

    def update(self, db: Session, product_id: int, product_update: ProductUpdate) -> Optional[Product]:
        product = self.get_by_id(db, product_id)
        if not product:
            return None
        update_data = product_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        db.commit()
        db.refresh(product)
        return product


class WarehouseService(BaseService[Warehouse]):
    def __init__(self):
        super().__init__(Warehouse)

    def create(self, db: Session, wh_in: WarehouseCreate) -> Warehouse:
        existing = db.query(Warehouse).filter(Warehouse.code == wh_in.code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Warehouse with code '{wh_in.code}' already exists",
            )
        warehouse = Warehouse(**wh_in.model_dump())
        return self.save(db, warehouse)

    def get_warehouses(self, db: Session, active_only: bool = False) -> List[Warehouse]:
        query = db.query(Warehouse)
        if active_only:
            query = query.filter(Warehouse.is_active.is_(True))
        return query.all()

    def update(self, db: Session, warehouse_id: int, wh_update: WarehouseUpdate) -> Optional[Warehouse]:
        warehouse = self.get_by_id(db, warehouse_id)
        if not warehouse:
            return None
        update_data = wh_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(warehouse, field, value)
        db.commit()
        db.refresh(warehouse)
        return warehouse


class DistributorService(BaseService[Distributor]):
    def __init__(self):
        super().__init__(Distributor)

    def create(self, db: Session, dist_in: DistributorCreate) -> Distributor:
        existing = db.query(Distributor).filter(Distributor.code == dist_in.code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Distributor with code '{dist_in.code}' already exists",
            )
        distributor = Distributor(**dist_in.model_dump())
        return self.save(db, distributor)

    def get_distributors(self, db: Session, active_only: bool = False) -> List[Distributor]:
        query = db.query(Distributor)
        if active_only:
            query = query.filter(Distributor.is_active.is_(True))
        return query.all()


class InventoryService(BaseService[Inventory]):
    def __init__(self):
        super().__init__(Inventory)

    def get_record(self, db: Session, warehouse_id: int, product_id: int) -> Optional[Inventory]:
        return (
            db.query(Inventory)
            .filter(
                Inventory.warehouse_id == warehouse_id,
                Inventory.product_id == product_id,
            )
            .first()
        )

    def set_or_update(self, db: Session, inv_in: InventoryCreate) -> Inventory:
        wh = db.query(Warehouse).filter(Warehouse.id == inv_in.warehouse_id).first()
        if not wh:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Warehouse with ID {inv_in.warehouse_id} not found",
            )
        prod = db.query(Product).filter(Product.id == inv_in.product_id).first()
        if not prod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {inv_in.product_id} not found",
            )

        inv = self.get_record(db, inv_in.warehouse_id, inv_in.product_id)
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

    def adjust_stock(self, db: Session, warehouse_id: int, product_id: int, delta: int) -> Inventory:
        inv = self.get_record(db, warehouse_id, product_id)
        if not inv:
            if delta < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot decrease stock for non-existent inventory record",
                )
            inv = Inventory(warehouse_id=warehouse_id, product_id=product_id, quantity=delta)
            db.add(inv)
        else:
            try:
                inv.adjust(delta)
            except ValueError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        db.commit()
        db.refresh(inv)
        return inv

    def reserve(self, db: Session, warehouse_id: int, product_id: int, quantity: int) -> bool:
        inv = self.get_record(db, warehouse_id, product_id)
        if not inv or not inv.reserve(quantity):
            return False
        db.commit()
        return True

    def release(self, db: Session, warehouse_id: int, product_id: int, quantity: int) -> bool:
        inv = self.get_record(db, warehouse_id, product_id)
        if not inv:
            return False
        inv.release(quantity)
        db.commit()
        return True

    def deduct(self, db: Session, warehouse_id: int, product_id: int, quantity: int) -> bool:
        inv = self.get_record(db, warehouse_id, product_id)
        if not inv or not inv.deduct(quantity):
            return False
        db.commit()
        return True

    def get_stock_alerts(self, db: Session) -> List[LowStockAlert]:
        alerts = []
        inventories = db.query(Inventory).all()
        for inv in inventories:
            status_label = inv.stock_status
            if status_label in ("CRITICAL", "LOW"):
                suggested = max(inv.safety_stock * 2 - inv.available_quantity, 10)
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


# Singleton instances
product_service = ProductService()
warehouse_service = WarehouseService()
distributor_service = DistributorService()
inventory_service = InventoryService()


# =============================================================================
# Functional Facades (Backward Compatibility)
# =============================================================================
def create_product(db: Session, product_in: ProductCreate) -> Product:
    return product_service.create(db, product_in)


def get_product(db: Session, product_id: int) -> Optional[Product]:
    return product_service.get_by_id(db, product_id)


def get_product_by_sku(db: Session, sku: str) -> Optional[Product]:
    return product_service.get_by_sku(db, sku)


def get_products(db: Session, skip: int = 0, limit: int = 100) -> List[Product]:
    return product_service.get_all(db, skip=skip, limit=limit)


def update_product(db: Session, product_id: int, product_update: ProductUpdate) -> Optional[Product]:
    return product_service.update(db, product_id, product_update)


def create_warehouse(db: Session, wh_in: WarehouseCreate) -> Warehouse:
    return warehouse_service.create(db, wh_in)


def get_warehouse(db: Session, warehouse_id: int) -> Optional[Warehouse]:
    return warehouse_service.get_by_id(db, warehouse_id)


def get_warehouses(db: Session, active_only: bool = False) -> List[Warehouse]:
    return warehouse_service.get_warehouses(db, active_only=active_only)


def update_warehouse(db: Session, warehouse_id: int, wh_update: WarehouseUpdate) -> Optional[Warehouse]:
    return warehouse_service.update(db, warehouse_id, wh_update)


def create_distributor(db: Session, dist_in: DistributorCreate) -> Distributor:
    return distributor_service.create(db, dist_in)


def get_distributor(db: Session, distributor_id: int) -> Optional[Distributor]:
    return distributor_service.get_by_id(db, distributor_id)


def get_distributors(db: Session, active_only: bool = False) -> List[Distributor]:
    return distributor_service.get_distributors(db, active_only=active_only)


def set_or_update_inventory(db: Session, inv_in: InventoryCreate) -> Inventory:
    return inventory_service.set_or_update(db, inv_in)


def adjust_stock(db: Session, warehouse_id: int, product_id: int, delta: int) -> Inventory:
    return inventory_service.adjust_stock(db, warehouse_id, product_id, delta)


def reserve_stock(db: Session, warehouse_id: int, product_id: int, quantity: int) -> bool:
    return inventory_service.reserve(db, warehouse_id, product_id, quantity)


def release_reserved_stock(db: Session, warehouse_id: int, product_id: int, quantity: int) -> bool:
    return inventory_service.release(db, warehouse_id, product_id, quantity)


def deduct_stock(db: Session, warehouse_id: int, product_id: int, quantity: int) -> bool:
    return inventory_service.deduct(db, warehouse_id, product_id, quantity)


def get_warehouse_stock(db: Session, warehouse_id: int) -> List[Inventory]:
    return db.query(Inventory).filter(Inventory.warehouse_id == warehouse_id).all()


def get_all_inventory(db: Session, skip: int = 0, limit: int = 100) -> List[Inventory]:
    return inventory_service.get_all(db, skip=skip, limit=limit)


def get_stock_alerts(db: Session) -> List[LowStockAlert]:
    return inventory_service.get_stock_alerts(db)
