"""
AI Order Agent:
Performs automated order validation, anomaly detection, priority evaluation,
risk scoring, and decision support.
Applies:
- Inheritance: Subclasses BaseAgent.
- Abstraction & Polymorphism: Implements abstract run() and get_health_status() contracts.
- Encapsulation: Protects anomaly detection algorithms, scoring formulas, and LLM reasoning.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.order import Order, OrderPriority
from app.schemas.order_schema import OrderAgentAnalysis
from app.agents.base_agent import BaseAgent
from app.agents.reasoning import ReasoningEngine


class OrderAgent(BaseAgent):
    """
    Intelligent Agent for Order Processing and Quality Assessment.
    Operates heuristically or utilizes LLM reasoning when configured.
    """

    def __init__(self, reasoning_engine: Optional[ReasoningEngine] = None):
        super().__init__(
            name="Order Quality Agent",
            description="Evaluates cargo risks, cold-chain compliance, priority tiers, and anomalies.",
            agent_type="ORDER_VALIDATION",
            reasoning_engine=reasoning_engine,
        )

    @property
    def llm_enabled(self) -> bool:
        return bool(settings.ENABLE_LLM_AGENT and settings.OPENAI_API_KEY)

    def run(self, db: Session, **kwargs) -> OrderAgentAnalysis:
        """
        Polymorphic execution entrypoint.
        Accepts either 'order' (Order model instance) or 'order_id' (int).
        """
        order = kwargs.get("order")
        if not order and "order_id" in kwargs:
            order = db.query(Order).filter(Order.id == kwargs["order_id"]).first()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OrderAgent requires a valid 'order' or 'order_id' parameter",
            )
        return self.analyze_order(db, order)

    def analyze_order(self, db: Session, order: Order) -> OrderAgentAnalysis:
        self._increment_executions()
        anomalies: List[str] = []
        cold_chain_required = False
        total_weight = 0.0
        total_volume = 0.0
        risk_score = 0.0

        # Check total items and values
        if not order.items or len(order.items) == 0:
            anomalies.append("Order contains 0 items.")
            risk_score += 0.8

        total_units = 0
        for item in order.items or []:
            total_units += item.quantity
            if item.product:
                total_weight += item.product.weight_kg * item.quantity
                total_volume += item.product.volume_m3 * item.quantity
                if item.product.is_temperature_controlled:
                    cold_chain_required = True

            # Quantity anomaly check
            if item.quantity > 500:
                anomalies.append(
                    f"Unusually large volume for item (Product ID {item.product_id}: {item.quantity} units)."
                )
                risk_score += 0.2

        if order.total_amount > settings.HIGH_VALUE_ORDER_THRESHOLD:
            anomalies.append(
                f"High-value order (${order.total_amount:,.2f}) exceeding threshold (${settings.HIGH_VALUE_ORDER_THRESHOLD:,.2f})."
            )
            risk_score += 0.15

        # Priority reasoning
        distributor_tier = order.distributor.tier_normalized if order.distributor else "STANDARD"
        recommended_priority = OrderPriority.NORMAL.value

        if distributor_tier in ("VIP", "GOLD") or cold_chain_required:
            recommended_priority = OrderPriority.HIGH.value
        if cold_chain_required and distributor_tier == "VIP":
            recommended_priority = OrderPriority.URGENT.value

        # Calculate final risk score clamped to [0.0, 1.0]
        risk_score = min(round(risk_score, 2), 1.0)
        is_valid = (risk_score < 0.7) and (len(order.items or []) > 0)

        # Generate reasoning narrative via encapsulated reasoning engine
        reasoning_context = {
            "order_number": order.order_number,
            "client_name": order.distributor.name if order.distributor else "N/A",
            "client_tier": distributor_tier,
            "total_amount": order.total_amount,
            "total_weight_kg": order.total_weight_kg,
            "cold_chain_required": cold_chain_required,
            "risk_score": risk_score,
            "anomalies": anomalies,
        }
        recommendation = self.explain(reasoning_context)

        # Update order with notes
        order.ai_analysis_notes = recommendation
        if order.priority != recommended_priority and order.priority == OrderPriority.NORMAL.value:
            order.priority = recommended_priority
        db.commit()

        return OrderAgentAnalysis(
            order_id=order.id,
            order_number=order.order_number,
            is_valid=is_valid,
            recommended_priority=recommended_priority,
            estimated_total_weight_kg=round(total_weight, 2),
            estimated_total_volume_m3=round(total_volume, 3),
            cold_chain_required=cold_chain_required,
            anomalies_detected=anomalies,
            fulfillment_risk_score=risk_score,
            ai_recommendation=recommendation,
        )

    def get_health_status(self) -> Dict[str, Any]:
        return {
            "agent_name": self._name,
            "type": self._agent_type,
            "status": "HEALTHY",
            "executions_performed": self._execution_count,
            "llm_reasoning_active": self.llm_enabled,
        }


order_agent = OrderAgent()
