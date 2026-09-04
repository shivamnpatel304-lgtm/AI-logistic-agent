"""
AI Allocation Agent:
Optimizes multi-warehouse order fulfillment, balances delivery distance against
warehouse inventory reserves, and minimizes split shipments.
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.order import Order
from app.schemas.allocation_schema import OrderAllocationResult
from app.services.allocation_service import allocate_order


class AllocationAgent:
    """
    Intelligent Agent for Order Allocation and Sourcing Optimization.
    """

    def __init__(self):
        self.llm_enabled = bool(settings.ENABLE_LLM_AGENT and settings.OPENAI_API_KEY)

    def optimize_order_fulfillment(
        self,
        db: Session,
        order_id: int,
        max_radius_km: float = 500.0,
        prefer_single_warehouse: bool = True,
        execute_allocation: bool = True,
    ) -> OrderAllocationResult:
        """
        Executes heuristic allocation optimization and enhances with agent explanations.
        """
        result = allocate_order(
            db=db,
            order_id=order_id,
            max_radius_km=max_radius_km,
            prefer_single_warehouse=prefer_single_warehouse,
            execute_reservation=execute_allocation,
        )

        # Enhance optimization notes with agent intelligence
        if result.is_fully_allocated:
            if len(result.fulfillment_centers) == 1:
                summary = (
                    f"Agent Optimization Succeeded: 100% consolidated dispatch from "
                    f"'{result.fulfillment_centers[0]}'. Minimizes freight costs and carrier fragmentation."
                )
            else:
                summary = (
                    f"Agent Optimization Completed: Multi-node fulfillment across "
                    f"{len(result.fulfillment_centers)} centers ({', '.join(result.fulfillment_centers)}) "
                    f"to ensure complete customer order satisfaction without stockout."
                )
        else:
            unfulfilled = result.total_items_requested - result.total_items_allocated
            summary = (
                f"Agent Warning: Partial fulfillment ({result.total_items_allocated}/{result.total_items_requested} units allocated). "
                f"{unfulfilled} units remain unfulfilled due to network stock shortages within {max_radius_km}km radius."
            )

        result.optimization_notes = summary
        return result


allocation_agent = AllocationAgent()
