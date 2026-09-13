"""
Order and OrderItem database models.
Applies:
- Inheritance: Inherits common columns and behaviors from BaseEntity.
- Encapsulation: Encapsulates order state machine, transition invariants, and cold-chain calculations.
"""
import enum
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseEntity


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    ALLOCATED = "ALLOCATED"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class OrderPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


# Finite State Machine Allowed Transitions
_VALID_TRANSITIONS = {
    OrderStatus.PENDING.value: {
        OrderStatus.VALIDATED.value,
        OrderStatus.ALLOCATED.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.VALIDATED.value: {
        OrderStatus.ALLOCATED.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.ALLOCATED.value: {
        OrderStatus.DISPATCHED.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.DISPATCHED.value: {
        OrderStatus.DELIVERED.value,
    },
    OrderStatus.DELIVERED.value: set(),
    OrderStatus.CANCELLED.value: set(),
}


class Order(BaseEntity):
    __tablename__ = "orders"

    order_number = Column(String(64), unique=True, index=True, nullable=False)
    distributor_id = Column(Integer, ForeignKey("distributors.id"), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    delivery_address = Column(String(500), nullable=False)
    delivery_latitude = Column(Float, nullable=False)
    delivery_longitude = Column(Float, nullable=False)
    status = Column(String(50), default=OrderStatus.PENDING.value, index=True)
    priority = Column(String(50), default=OrderPriority.NORMAL.value)
    total_amount = Column(Float, default=0.0)
    total_weight_kg = Column(Float, default=0.0)
    special_instructions = Column(Text, nullable=True)
    ai_analysis_notes = Column(Text, nullable=True)

    # Relationships
    distributor = relationship("Distributor", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    # =========================================================================
    # Encapsulated Domain Properties
    # =========================================================================
    @property
    def is_cancellable(self) -> bool:
        """Returns True if the order can be cancelled in its current state."""
        return self.status not in (
            OrderStatus.DISPATCHED.value,
            OrderStatus.DELIVERED.value,
            OrderStatus.CANCELLED.value,
        )

    @property
    def is_cold_chain_required(self) -> bool:
        """Encapsulated check across all items for cold chain requirement."""
        for item in self.items or []:
            if item.product and item.product.is_temperature_controlled:
                return True
        return False

    @property
    def total_units_requested(self) -> int:
        """Sum of all ordered product quantities."""
        return sum(item.quantity for item in self.items or [])

    @property
    def total_units_allocated(self) -> int:
        """Sum of all successfully allocated item quantities."""
        return sum(item.allocated_quantity for item in self.items or [])

    @property
    def is_fully_allocated(self) -> bool:
        """Returns True if all requested units have warehouse allocations."""
        return (self.total_units_requested > 0) and (self.total_units_allocated == self.total_units_requested)

    # =========================================================================
    # Encapsulated State Machine Transitions
    # =========================================================================
    def can_transition_to(self, target_status: OrderStatus) -> bool:
        """Validates if status transition is compliant with order lifecycle."""
        allowed = _VALID_TRANSITIONS.get(self.status, set())
        return target_status.value in allowed

    def transition_to(self, target_status: OrderStatus) -> None:
        """
        Transitions the order state. Raises ValueError on illegal lifecycle jumps.
        """
        if not self.can_transition_to(target_status):
            raise ValueError(
                f"Illegal order state transition from '{self.status}' to '{target_status.value}'."
            )
        self.status = target_status.value

    def cancel(self) -> None:
        """Encapsulates cancellation validation and state change."""
        if not self.is_cancellable:
            raise ValueError(f"Cannot cancel order in status '{self.status}'.")
        self.status = OrderStatus.CANCELLED.value

    def recalculate_metrics(self) -> None:
        """Encapsulates recalculation of total price and cargo weight."""
        total_amt = 0.0
        total_wt = 0.0
        for item in self.items or []:
            total_amt += item.unit_price * item.quantity
            if item.product:
                total_wt += item.product.weight_kg * item.quantity
        self.total_amount = round(total_amt, 2)
        self.total_weight_kg = round(total_wt, 2)

    def __repr__(self) -> str:
        return f"<Order(order_number='{self.order_number}', status='{self.status}', priority='{self.priority}')>"


class OrderItem(BaseEntity):
    __tablename__ = "order_items"

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False, default=0.0)
    allocated_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    allocated_quantity = Column(Integer, default=0)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    allocated_warehouse = relationship("Warehouse")

    @property
    def line_total(self) -> float:
        return round(self.unit_price * self.quantity, 2)

    @property
    def unfulfilled_quantity(self) -> int:
        return max(0, self.quantity - self.allocated_quantity)

    @property
    def is_fully_allocated(self) -> bool:
        return self.allocated_quantity >= self.quantity

    def __repr__(self) -> str:
        return (
            f"<OrderItem(order_id={self.order_id}, prod_id={self.product_id}, "
            f"qty={self.quantity}, alloc={self.allocated_quantity})>"
        )
