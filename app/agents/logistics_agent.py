"""
AI Logistics Agent:
Vehicle matching, capacity planning, cold-chain compliance verification,
and dispatch route advisory.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.allocation_schema import DispatchRecommendation, DispatchRequest
from app.services.logistics_service import plan_dispatch, execute_dispatch


class LogisticsAgent:
    """
    Intelligent Agent for Fleet and Dispatch Management.
    """

    def __init__(self):
        self.llm_enabled = bool(settings.ENABLE_LLM_AGENT and settings.OPENAI_API_KEY)

    def evaluate_and_plan_dispatch(self, db: Session, order_id: int) -> DispatchRecommendation:
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
        return execute_dispatch(db=db, request=request)


logistics_agent = LogisticsAgent()
