"""
AI Allocation Agent:
Optimizes multi-warehouse order fulfillment, balances delivery distance against
warehouse inventory reserves, and minimizes split shipments.
Applies:
- Inheritance: Subclasses BaseAgent.
- Abstraction & Polymorphism: Implements abstract run() and get_health_status() contracts.
- Encapsulation: Encapsulates fulfillment optimization heuristics and consolidation narratives.
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.allocation_schema import OrderAllocationResult
from app.services.allocation_service import allocate_order
from app.agents.base_agent import BaseAgent
from app.agents.reasoning import ReasoningEngine


class AllocationAgent(BaseAgent):
    """
    Intelligent Agent for Order Allocation and Sourcing Optimization.
    """

    def __init__(self, reasoning_engine: Optional[ReasoningEngine] = None):
        super().__init__(
            name="Sourcing & Allocation Agent",
            description="Executes optimal facility selection, inventory reservation, and split mitigation.",
            agent_type="FULFILLMENT_ALLOCATION",
            reasoning_engine=reasoning_engine,
        )

    @property
    def llm_enabled(self) -> bool:
        return bool(settings.ENABLE_LLM_AGENT and settings.OPENAI_API_KEY)

    def run(self, db: Session, **kwargs) -> OrderAllocationResult:
        """Polymorphic execution entrypoint."""
        order_id = kwargs.get("order_id")
        if not order_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AllocationAgent requires 'order_id' in execution arguments",
            )
        return self.optimize_order_fulfillment(
            db=db,
            order_id=order_id,
            max_radius_km=kwargs.get("max_radius_km", 500.0),
            prefer_single_warehouse=kwargs.get("prefer_single_warehouse", True),
            execute_allocation=kwargs.get("execute_allocation", True),
        )

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
        self._increment_executions()
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

    def get_health_status(self) -> Dict[str, Any]:
        return {
            "agent_name": self._name,
            "type": self._agent_type,
            "status": "HEALTHY",
            "executions_performed": self._execution_count,
            "llm_reasoning_active": self.llm_enabled,
        }


allocation_agent = AllocationAgent()
