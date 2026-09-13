"""
AI Logistics Agent:
Vehicle matching, capacity planning, cold-chain compliance verification,
and dispatch route advisory.
Applies:
- Inheritance: Subclasses BaseAgent.
- Abstraction & Polymorphism: Implements abstract run() and get_health_status() contracts.
- Encapsulation: Encapsulates carrier selection rules, cold chain alerts, and driver hours advisories.
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.allocation_schema import DispatchRecommendation, DispatchRequest
from app.services.logistics_service import plan_dispatch, execute_dispatch
from app.agents.base_agent import BaseAgent
from app.agents.reasoning import ReasoningEngine


class LogisticsAgent(BaseAgent):
    """
    Intelligent Agent for Fleet and Dispatch Management.
    """

    def __init__(self, reasoning_engine: Optional[ReasoningEngine] = None):
        super().__init__(
            name="Fleet & Dispatch Agent",
            description="Matches vehicles to cargo specifications, verifies reefer constraints, and routes.",
            agent_type="FLEET_LOGISTICS",
            reasoning_engine=reasoning_engine,
        )

    @property
    def llm_enabled(self) -> bool:
        return bool(settings.ENABLE_LLM_AGENT and settings.OPENAI_API_KEY)

    def run(self, db: Session, **kwargs) -> Any:
        """Polymorphic execution entrypoint."""
        if "dispatch_request" in kwargs:
            return self.dispatch_order(db, kwargs["dispatch_request"])
        if "order_id" in kwargs:
            return self.evaluate_and_plan_dispatch(db, kwargs["order_id"])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LogisticsAgent requires either 'order_id' or 'dispatch_request'",
        )

    def evaluate_and_plan_dispatch(self, db: Session, order_id: int) -> DispatchRecommendation:
        self._increment_executions()
        plan = plan_dispatch(db=db, order_id=order_id)

        # Enhance dispatch plan with logistics advisory
        advisories = [plan.dispatch_notes]

        if plan.requires_reefer and plan.vehicle_type == "REEFER":
            advisories.append("Cold chain integrity verified: Temperature data logger pre-trip check required.")
        elif plan.requires_reefer and plan.vehicle_type != "REEFER":
            advisories.append("URGENT: Cold chain breach danger! Dispatch halted until Reefer capacity arrives.")

        if plan.estimated_transit_hours > 8.0:
            advisories.append("Long-haul transit (>8h): Co-driver or mandatory rest stop scheduling recommended.")

        plan.dispatch_notes = " | ".join(filter(None, advisories))
        return plan

    def dispatch_order(self, db: Session, request: DispatchRequest):
        self._increment_executions()
        return execute_dispatch(db=db, request=request)

    def get_health_status(self) -> Dict[str, Any]:
        return {
            "agent_name": self._name,
            "type": self._agent_type,
            "status": "HEALTHY",
            "executions_performed": self._execution_count,
            "llm_reasoning_active": self.llm_enabled,
        }


logistics_agent = LogisticsAgent()
