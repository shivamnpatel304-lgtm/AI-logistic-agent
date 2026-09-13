"""
Allocation Strategies implementing Strategy Design Pattern.
Applies:
- Abstraction: AbstractAllocationStrategy defines the contract for fulfillment algorithms.
- Inheritance: Concrete strategies (SingleSource, MultiNodeProximity) inherit from AbstractAllocationStrategy.
- Polymorphism: Different allocation algorithms can be executed interchangeably through .allocate().
- Encapsulation: Distance calculations and warehouse selection logic are encapsulated within classes.
"""
import math
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.warehouse import Warehouse
from app.models.inventory import Inventory
from app.schemas.allocation_schema import ItemAllocationDetail, OrderAllocationResult


class DistanceCalculator:
    """
    Encapsulates geodesic spatial distance calculations using the Haversine formula.
    """
    EARTH_RADIUS_KM = 6371.0

    @classmethod
    def calculate(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(cls.EARTH_RADIUS_KM * c, 2)


class AbstractAllocationStrategy(ABC):
    """
    Abstract strategy defining fulfillment and inventory reservation contract.
    """

    @abstractmethod
    def allocate(
        self,
        db: Session,
        order: Order,
        warehouses: List[Warehouse],
        max_radius_km: float = 500.0,
        execute_reservation: bool = True,
    ) -> OrderAllocationResult:
        """
        Executes order fulfillment allocation according to strategy rules.
        """
        pass

    def _calculate_warehouse_distances(
        self, order: Order, warehouses: List[Warehouse]
    ) -> Dict[int, float]:
        """Encapsulated helper to compute distance from each warehouse to order destination."""
        distances = {}
        for wh in warehouses:
            distances[wh.id] = DistanceCalculator.calculate(
                order.delivery_latitude,
                order.delivery_longitude,
                wh.latitude,
                wh.longitude,
            )
        return distances


class SingleSourceAllocationStrategy(AbstractAllocationStrategy):
    """
    Strategy that attempts 100% consolidated fulfillment from a single closest warehouse
    to minimize parcel fragmentation and transportation overhead.
    """

    def allocate(
        self,
        db: Session,
        order: Order,
        warehouses: List[Warehouse],
        max_radius_km: float = 500.0,
        execute_reservation: bool = True,
    ) -> OrderAllocationResult:
        warehouse_distances = self._calculate_warehouse_distances(order, warehouses)
        sorted_warehouses = sorted(warehouses, key=lambda wh: warehouse_distances[wh.id])

        chosen_wh: Optional[Warehouse] = None

        for wh in sorted_warehouses:
            if warehouse_distances[wh.id] > max_radius_km:
                continue

            can_fulfill_all = True
            for item in order.items or []:
                inv = (
                    db.query(Inventory)
                    .filter(
                        Inventory.warehouse_id == wh.id,
                        Inventory.product_id == item.product_id,
                    )
                    .first()
                )
                if not inv or inv.available_quantity < item.quantity:
                    can_fulfill_all = False
                    break

            if can_fulfill_all:
                chosen_wh = wh
                break

        if not chosen_wh:
            # Fall back to multi-node proximity strategy if single node cannot satisfy order
            fallback = MultiNodeProximityAllocationStrategy()
            result = fallback.allocate(db, order, warehouses, max_radius_km, execute_reservation)
            result.optimization_notes = (
                "Single warehouse consolidation infeasible due to SKU availability; "
                + result.optimization_notes
            )
            return result

        # Consolidate under chosen warehouse
        allocation_details: List[ItemAllocationDetail] = []
        total_requested = 0
        total_allocated = 0
        dist = warehouse_distances[chosen_wh.id]

        for item in order.items or []:
            total_requested += item.quantity
            total_allocated += item.quantity

            if execute_reservation:
                inv = (
                    db.query(Inventory)
                    .filter(
                        Inventory.warehouse_id == chosen_wh.id,
                        Inventory.product_id == item.product_id,
                    )
                    .first()
                )
                if inv:
                    inv.reserve(item.quantity)
                item.allocated_warehouse_id = chosen_wh.id
                item.allocated_quantity = item.quantity

            allocation_details.append(
                ItemAllocationDetail(
                    product_id=item.product_id,
                    product_name=item.product.name if item.product else f"Product {item.product_id}",
                    requested_quantity=item.quantity,
                    allocated_quantity=item.quantity,
                    unfulfilled_quantity=0,
                    warehouse_id=chosen_wh.id,
                    warehouse_name=chosen_wh.name,
                    distance_km=dist,
                )
            )

        if execute_reservation:
            order.status = OrderStatus.ALLOCATED.value
            db.commit()
            db.refresh(order)

        return OrderAllocationResult(
            order_id=order.id,
            order_number=order.order_number,
            is_fully_allocated=True,
            total_items_requested=total_requested,
            total_items_allocated=total_allocated,
            allocations=allocation_details,
            fulfillment_centers=[chosen_wh.name],
            optimization_notes=f"Optimal single-warehouse consolidated fulfillment from '{chosen_wh.name}' ({dist} km away).",
        )


class MultiNodeProximityAllocationStrategy(AbstractAllocationStrategy):
    """
    Strategy that distributes allocations across nearest regional fulfillment centers
    when individual facilities cannot fulfill the full inventory demand.
    """

    def allocate(
        self,
        db: Session,
        order: Order,
        warehouses: List[Warehouse],
        max_radius_km: float = 500.0,
        execute_reservation: bool = True,
    ) -> OrderAllocationResult:
        warehouse_distances = self._calculate_warehouse_distances(order, warehouses)
        sorted_warehouses = sorted(warehouses, key=lambda wh: warehouse_distances[wh.id])

        allocation_details: List[ItemAllocationDetail] = []
        fulfillment_centers_set = set()
        total_requested = 0
        total_allocated = 0

        for item in order.items or []:
            total_requested += item.quantity
            remaining_qty = item.quantity
            item_allocated = 0

            for wh in sorted_warehouses:
                dist = warehouse_distances[wh.id]
                if dist > max_radius_km:
                    continue

                inv = (
                    db.query(Inventory)
                    .filter(
                        Inventory.warehouse_id == wh.id,
                        Inventory.product_id == item.product_id,
                    )
                    .first()
                )

                if inv and inv.available_quantity > 0:
                    alloc_qty = min(remaining_qty, inv.available_quantity)
                    remaining_qty -= alloc_qty
                    item_allocated += alloc_qty
                    fulfillment_centers_set.add(wh.name)

                    if execute_reservation:
                        inv.reserve(alloc_qty)
                        if not item.allocated_warehouse_id:
                            item.allocated_warehouse_id = wh.id
                        item.allocated_quantity += alloc_qty

                    allocation_details.append(
                        ItemAllocationDetail(
                            product_id=item.product_id,
                            product_name=item.product.name if item.product else f"Product {item.product_id}",
                            requested_quantity=item.quantity,
                            allocated_quantity=alloc_qty,
                            unfulfilled_quantity=remaining_qty,
                            warehouse_id=wh.id,
                            warehouse_name=wh.name,
                            distance_km=dist,
                        )
                    )

                    if remaining_qty <= 0:
                        break

            total_allocated += item_allocated
            if remaining_qty > 0 and not any(d.product_id == item.product_id for d in allocation_details):
                allocation_details.append(
                    ItemAllocationDetail(
                        product_id=item.product_id,
                        product_name=item.product.name if item.product else f"Product {item.product_id}",
                        requested_quantity=item.quantity,
                        allocated_quantity=item_allocated,
                        unfulfilled_quantity=remaining_qty,
                        warehouse_id=None,
                        warehouse_name=None,
                        distance_km=None,
                    )
                )

        is_fully_allocated = (total_allocated == total_requested)

        if execute_reservation:
            if is_fully_allocated:
                order.status = OrderStatus.ALLOCATED.value
            elif total_allocated > 0:
                order.status = OrderStatus.VALIDATED.value
            db.commit()
            db.refresh(order)

        notes = (
            f"Multi-node proximity fulfillment across {len(fulfillment_centers_set)} centers: "
            f"({', '.join(fulfillment_centers_set)})."
            if is_fully_allocated
            else f"Partial multi-node fulfillment: {total_allocated}/{total_requested} units allocated."
        )

        return OrderAllocationResult(
            order_id=order.id,
            order_number=order.order_number,
            is_fully_allocated=is_fully_allocated,
            total_items_requested=total_requested,
            total_items_allocated=total_allocated,
            allocations=allocation_details,
            fulfillment_centers=list(fulfillment_centers_set),
            optimization_notes=notes,
        )


class AllocationStrategyFactory:
    """
    Factory class providing polymorphic strategy creation.
    """

    @staticmethod
    def create(prefer_single_warehouse: bool = True) -> AbstractAllocationStrategy:
        if prefer_single_warehouse:
            return SingleSourceAllocationStrategy()
        return MultiNodeProximityAllocationStrategy()
