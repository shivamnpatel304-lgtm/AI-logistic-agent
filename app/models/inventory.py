"""
Inventory database model.
Applies:
- Inheritance: Inherits common columns and behaviors from BaseEntity.
- Encapsulation: Encapsulates stock transactions (reserve, release, deduct) and health state calculations.
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseEntity


class Inventory(BaseEntity):
    __tablename__ = "inventories"

    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    reserved_quantity = Column(Integer, nullable=False, default=0)
    safety_stock = Column(Integer, nullable=False, default=20)
    reorder_point = Column(Integer, nullable=False, default=10)
    batch_number = Column(String(100), nullable=True)

    # Relationships
    warehouse = relationship("Warehouse", back_populates="inventory_records")
    product = relationship("Product", back_populates="inventory_items")

    # =========================================================================
    # Encapsulated Domain Properties
    # =========================================================================
    @property
    def available_quantity(self) -> int:
        """Units currently on hand and unreserved."""
        return max(0, self.quantity - self.reserved_quantity)

    @property
    def is_below_reorder_point(self) -> bool:
        """Indicates critical stock deficiency requiring immediate replenishment."""
        return self.available_quantity <= self.reorder_point

    @property
    def is_below_safety_stock(self) -> bool:
        """Indicates inventory level has dipped into safety reserve."""
        return self.available_quantity <= self.safety_stock

    @property
    def stock_status(self) -> str:
        """Determines categorical inventory health status."""
        if self.is_below_reorder_point:
            return "CRITICAL"
        if self.is_below_safety_stock:
            return "LOW"
        return "OPTIMAL"

    # =========================================================================
    # Encapsulated Domain Mutation Methods
    # =========================================================================
    def reserve(self, qty: int) -> bool:
        """
        Safely reserves inventory for an order allocation.
        Returns True if successful, False if insufficient available stock.
        """
        if qty <= 0:
            return True
        if self.available_quantity < qty:
            return False
        self.reserved_quantity += qty
        return True

    def release(self, qty: int) -> bool:
        """
        Safely releases previously reserved inventory back to available pool.
        """
        if qty <= 0:
            return True
        self.reserved_quantity = max(0, self.reserved_quantity - qty)
        return True

    def deduct(self, qty: int) -> bool:
        """
        Permanently deducts stock upon physical carrier dispatch.
        Simultaneously decrements total on-hand and reserved amounts.
        """
        if qty <= 0:
            return True
        if self.quantity < qty:
            return False
        self.quantity -= qty
        self.reserved_quantity = max(0, self.reserved_quantity - qty)
        return True

    def adjust(self, delta: int) -> int:
        """
        Adjusts on-hand stock upwards or downwards.
        Raises ValueError if reduction would fall below already-reserved quantities.
        """
        new_quantity = self.quantity + delta
        if new_quantity < self.reserved_quantity:
            raise ValueError(
                f"Cannot reduce stock to {new_quantity}: {self.reserved_quantity} units are already reserved."
            )
        self.quantity = new_quantity
        return self.quantity

    def __repr__(self) -> str:
        return (
            f"<Inventory(wh={self.warehouse_id}, prod={self.product_id}, "
            f"qty={self.quantity}, reserved={self.reserved_quantity})>"
        )
