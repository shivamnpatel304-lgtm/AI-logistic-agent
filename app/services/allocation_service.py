"""
Allocation service handling geospatial optimization, inventory fulfillment strategies, and warehouse rebalancing.
"""
import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.order import Order, OrderStatus
from app.models.warehouse import Warehouse
from app.models.inventory import Inventory
from app.schemas.allocation_schema import (
    ItemAllocationDetail,
    OrderAllocationResult,
    AllocationSimulateRequest,
)
from app.schemas.inventory_schema import RebalanceRecommendation
from app.services.inventory_service import reserve_stock, get_warehouse


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two geographical points using the Haversine formula.
    """
    R = 6371.0  # Earth's radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


def allocate_order(
    db: Session,
    order_id: int,
    max_radius_km: float = 500.0,
    prefer_single_warehouse: bool = True,
    execute_reservation: bool = True,
) -> OrderAllocationResult:
    """
    Calculates and optionally executes optimal warehouse inventory allocation for an order.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found"
        )

    if order.status in (OrderStatus.DISPATCHED.value, OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot allocate order in '{order.status}' status"
        )

    # Fetch active warehouses
    warehouses = db.query(Warehouse).filter(Warehouse.is_active.is_(True)).all()
    if not warehouses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active warehouses available for allocation"
        )

    # Sort warehouses by proximity to delivery location
    warehouse_distances = {}
    for wh in warehouses:
        dist = calculate_distance_km(
            order.delivery_latitude,
            order.delivery_longitude,
            wh.latitude,
            wh.longitude
        )
        warehouse_distances[wh.id] = dist

    sorted_warehouses = sorted(warehouses, key=lambda wh: warehouse_distances[wh.id])

    # Check for single-warehouse fulfillment feasibility
    single_source_wh: Optional[Warehouse] = None
    if prefer_single_warehouse:
        for wh in sorted_warehouses:
            can_fulfill_all = True
            for item in order.items:
                inv = db.query(Inventory).filter(
                    Inventory.warehouse_id == wh.id,
                    Inventory.product_id == item.product_id
                ).first()
                if not inv or inv.available_quantity < item.quantity:
                    can_fulfill_all = False
                    break
            if can_fulfill_all:
                single_source_wh = wh
                break

    allocation_details: List[ItemAllocationDetail] = []
    fulfillment_centers_set = set()
    total_requested = 0
    total_allocated = 0

    if single_source_wh:
        # Full order fulfilled from closest single warehouse
        for item in order.items:
            total_requested += item.quantity
            total_allocated += item.quantity
            dist = warehouse_distances[single_source_wh.id]
            fulfillment_centers_set.add(single_source_wh.name)

            if execute_reservation:
                item.allocated_warehouse_id = single_source_wh.id
                item.allocated_quantity = item.quantity
                reserve_stock(db, single_source_wh.id, item.product_id, item.quantity)

            allocation_details.append(
                ItemAllocationDetail(
                    product_id=item.product_id,
                    product_name=item.product.name if item.product else f"Product {item.product_id}",
                    requested_quantity=item.quantity,
                    allocated_quantity=item.quantity,
                    unfulfilled_quantity=0,
                    warehouse_id=single_source_wh.id,
                    warehouse_name=single_source_wh.name,
                    distance_km=dist,
                )
            )
        opt_note = f"Optimal single-warehouse fulfillment from '{single_source_wh.name}' ({warehouse_distances[single_source_wh.id]} km away)."
    else:
        # Multi-warehouse allocation logic based on proximity
        opt_note = "Split-warehouse fulfillment required due to inventory distribution across regional nodes."
        for item in order.items:
            total_requested += item.quantity
            remaining_qty = item.quantity
            item_allocated = 0

            for wh in sorted_warehouses:
                dist = warehouse_distances[wh.id]
                if dist > max_radius_km:
                    continue

                inv = db.query(Inventory).filter(
                    Inventory.warehouse_id == wh.id,
                    Inventory.product_id == item.product_id
                ).first()

                if inv and inv.available_quantity > 0:
                    alloc_qty = min(remaining_qty, inv.available_quantity)
                    remaining_qty -= alloc_qty
                    item_allocated += alloc_qty
                    fulfillment_centers_set.add(wh.name)

                    if execute_reservation:
                        # If primary allocation not set, set it
                        if not item.allocated_warehouse_id:
                            item.allocated_warehouse_id = wh.id
                        item.allocated_quantity += alloc_qty
                        reserve_stock(db, wh.id, item.product_id, alloc_qty)

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
            order.status = OrderStatus.VALIDATED.value  # partially allocated
        db.commit()
        db.refresh(order)

    return OrderAllocationResult(
        order_id=order.id,
        order_number=order.order_number,
        is_fully_allocated=is_fully_allocated,
        total_items_requested=total_requested,
        total_items_allocated=total_allocated,
        allocations=allocation_details,
        fulfillment_centers=list(fulfillment_centers_set),
        optimization_notes=opt_note,
    )


def generate_rebalance_recommendations(db: Session) -> List[RebalanceRecommendation]:
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
                surplus.quantity -= 0  # just recommendation, not changing actual db here

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
