"""
Allocation and Fulfillment Service.
Applies:
- Abstraction & Polymorphism: Utilizes AbstractAllocationStrategy and AllocationStrategyFactory.
- Encapsulation: Encapsulates order fulfillment constraints, stock rebalancing computations, and geodesic calculations.
- Zero Regressions: Preserves module functions for backwards compatibility.
"""
from typing import List, Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.order import Order, OrderStatus
from app.models.warehouse import Warehouse
from app.models.inventory import Inventory
from app.schemas.allocation_schema import OrderAllocationResult
from app.schemas.inventory_schema import RebalanceRecommendation
from app.services.allocation_strategies import (
    DistanceCalculator,
    AllocationStrategyFactory,
)


class AllocationService:
    """
    Service responsible for intelligent inventory sourcing, network allocation, and stock rebalancing.
    """

    def __init__(self, strategy_factory: AllocationStrategyFactory = None):
        self._strategy_factory = strategy_factory or AllocationStrategyFactory()

    def allocate_order(
        self,
        db: Session,
        order_id: int,
        max_radius_km: float = 500.0,
        prefer_single_warehouse: bool = True,
        execute_reservation: bool = True,
    ) -> OrderAllocationResult:
        """
        Coordinates order fulfillment by choosing an allocation strategy polymorphically.
        """
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order with ID {order_id} not found",
            )

        if not order.is_cancellable and order.status in (
            OrderStatus.DISPATCHED.value,
            OrderStatus.DELIVERED.value,
            OrderStatus.CANCELLED.value,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot allocate order in '{order.status}' status",
            )

        warehouses = db.query(Warehouse).filter(Warehouse.is_active.is_(True)).all()
        if not warehouses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active warehouses available for allocation",
            )

        # Polymorphic strategy selection
        strategy = self._strategy_factory.create(prefer_single_warehouse=prefer_single_warehouse)
        return strategy.allocate(
            db=db,
            order=order,
            warehouses=warehouses,
            max_radius_km=max_radius_km,
            execute_reservation=execute_reservation,
        )

    def generate_rebalance_recommendations(self, db: Session) -> List[RebalanceRecommendation]:
        """
        Identifies inventory imbalances across warehouses and computes optimal transfers.
        """
        recommendations: List[RebalanceRecommendation] = []
        inventories = db.query(Inventory).all()

        # Group by product
        by_product: Dict[int, List[Inventory]] = {}
        for inv in inventories:
            by_product.setdefault(inv.product_id, []).append(inv)

        for product_id, inv_list in by_product.items():
            surplus_nodes = [i for i in inv_list if i.available_quantity > (i.safety_stock * 2)]
            deficit_nodes = [i for i in inv_list if i.available_quantity < i.safety_stock]

            for deficit in deficit_nodes:
                needed = deficit.safety_stock - deficit.available_quantity
                if needed <= 0:
                    continue

                for surplus in surplus_nodes:
                    excess = surplus.available_quantity - (surplus.safety_stock * 2)
                    if excess <= 0:
                        continue

                    transfer_qty = min(needed, excess)
                    needed -= transfer_qty

                    recommendations.append(
                        RebalanceRecommendation(
                            product_id=product_id,
                            product_name=deficit.product.name if deficit.product else f"Product {product_id}",
                            source_warehouse_id=surplus.warehouse_id,
                            source_warehouse_name=surplus.warehouse.name if surplus.warehouse else f"Warehouse {surplus.warehouse_id}",
                            target_warehouse_id=deficit.warehouse_id,
                            target_warehouse_name=deficit.warehouse.name if deficit.warehouse else f"Warehouse {deficit.warehouse_id}",
                            recommended_transfer_quantity=transfer_qty,
                            reason=f"Safety stock breach at target ({deficit.available_quantity}/{deficit.safety_stock}); excess stock available at source ({surplus.available_quantity}).",
                        )
                    )

                    if needed <= 0:
                        break

        return recommendations


# Singleton instance
allocation_service = AllocationService()


# =============================================================================
# Functional Facade (Backward Compatibility)
# =============================================================================
def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return DistanceCalculator.calculate(lat1, lon1, lat2, lon2)


def allocate_order(
    db: Session,
    order_id: int,
    max_radius_km: float = 500.0,
    prefer_single_warehouse: bool = True,
    execute_reservation: bool = True,
) -> OrderAllocationResult:
    return allocation_service.allocate_order(
        db=db,
        order_id=order_id,
        max_radius_km=max_radius_km,
        prefer_single_warehouse=prefer_single_warehouse,
        execute_reservation=execute_reservation,
    )


def generate_rebalance_recommendations(db: Session) -> List[RebalanceRecommendation]:
    return allocation_service.generate_rebalance_recommendations(db)
