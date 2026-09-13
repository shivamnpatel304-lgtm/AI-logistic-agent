"""
Order Management Service.
Applies:
- Inheritance: Subclasses BaseService[Order] to inherit standard entity persistence routines.
- Encapsulation: Encapsulates order generation, total calculations, and cancellation workflows.
- Zero Regressions: Retains top-level module function signatures for seamless backward compatibility.
"""
from datetime import datetime
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.order import Order, OrderItem, OrderStatus, OrderPriority
from app.models.distributor import Distributor
from app.models.product import Product
from app.schemas.order_schema import OrderCreate, OrderUpdate
from app.services.base_service import BaseService


class OrderService(BaseService[Order]):
    """
    Encapsulated Order Domain Service.
    """

    def __init__(self):
        super().__init__(Order)

    def generate_order_number(self) -> str:
        """Encapsulates unique order identifier creation."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M")
        unique_suffix = uuid.uuid4().hex[:6].upper()
        return f"ORD-{timestamp}-{unique_suffix}"

    def get_order(self, db: Session, order_id: int) -> Optional[Order]:
        return self.get_by_id(db, order_id)

    def get_by_order_number(self, db: Session, order_number: str) -> Optional[Order]:
        return db.query(Order).filter(Order.order_number == order_number).first()

    def list_orders(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[str] = None,
    ) -> List[Order]:
        query = db.query(Order)
        if status_filter:
            query = query.filter(Order.status == status_filter.upper())
        return query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

    def create_order(self, db: Session, order_in: OrderCreate) -> Order:
        """
        Validates client status, product catalog availability, calculates weights, and creates order.
        """
        distributor = db.query(Distributor).filter(Distributor.id == order_in.distributor_id).first()
        if not distributor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Distributor with ID {order_in.distributor_id} not found",
            )
        if not distributor.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Distributor '{distributor.name}' is currently inactive",
            )

        total_amount = 0.0
        total_weight_kg = 0.0
        order_items = []

        for item_in in order_in.items:
            product = db.query(Product).filter(Product.id == item_in.product_id).first()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {item_in.product_id} not found",
                )

            item_total = product.unit_price * item_in.quantity
            item_weight = product.weight_kg * item_in.quantity

            total_amount += item_total
            total_weight_kg += item_weight

            order_item = OrderItem(
                product_id=product.id,
                quantity=item_in.quantity,
                unit_price=product.unit_price,
                allocated_warehouse_id=None,
                allocated_quantity=0,
            )
            order_items.append(order_item)

        order = Order(
            order_number=self.generate_order_number(),
            distributor_id=order_in.distributor_id,
            customer_name=order_in.customer_name,
            delivery_address=order_in.delivery_address,
            delivery_latitude=order_in.delivery_latitude,
            delivery_longitude=order_in.delivery_longitude,
            status=OrderStatus.PENDING.value,
            priority=(order_in.priority or OrderPriority.NORMAL).value,
            total_amount=round(total_amount, 2),
            total_weight_kg=round(total_weight_kg, 2),
            special_instructions=order_in.special_instructions,
            items=order_items,
        )

        return self.save(db, order)

    def update_order(self, db: Session, order_id: int, order_update: OrderUpdate) -> Optional[Order]:
        order = self.get_order(db, order_id)
        if not order:
            return None

        if order_update.status:
            order.transition_to(order_update.status)
        if order_update.priority:
            order.priority = order_update.priority.value
        if order_update.special_instructions is not None:
            order.special_instructions = order_update.special_instructions

        db.commit()
        db.refresh(order)
        return order

    def cancel_order(self, db: Session, order_id: int) -> Optional[Order]:
        """
        Cancels an order and automatically releases all reserved warehouse stock.
        """
        from app.services.inventory_service import release_reserved_stock

        order = self.get_order(db, order_id)
        if not order:
            return None

        if order.status == OrderStatus.CANCELLED.value:
            return order

        if not order.is_cancellable:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel order in status '{order.status}'",
            )

        # Release allocated stock via inventory service
        for item in order.items or []:
            if item.allocated_warehouse_id and item.allocated_quantity > 0:
                release_reserved_stock(
                    db=db,
                    warehouse_id=item.allocated_warehouse_id,
                    product_id=item.product_id,
                    quantity=item.allocated_quantity,
                )
                item.allocated_quantity = 0
                item.allocated_warehouse_id = None

        order.cancel()
        db.commit()
        db.refresh(order)
        return order


# Singleton service instance
order_service = OrderService()


# =============================================================================
# Functional Facade (Backward Compatibility)
# =============================================================================
def generate_order_number() -> str:
    return order_service.generate_order_number()


def create_order(db: Session, order_in: OrderCreate) -> Order:
    return order_service.create_order(db, order_in)


def get_order(db: Session, order_id: int) -> Optional[Order]:
    return order_service.get_order(db, order_id)


def get_order_by_number(db: Session, order_number: str) -> Optional[Order]:
    return order_service.get_by_order_number(db, order_number)


def get_orders(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
) -> List[Order]:
    return order_service.list_orders(db, skip=skip, limit=limit, status_filter=status_filter)


def update_order(db: Session, order_id: int, order_update: OrderUpdate) -> Optional[Order]:
    return order_service.update_order(db, order_id, order_update)


def cancel_order(db: Session, order_id: int) -> Optional[Order]:
    return order_service.cancel_order(db, order_id)
