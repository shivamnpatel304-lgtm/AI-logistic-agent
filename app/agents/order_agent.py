"""
AI Order Agent:
Performs automated order validation, anomaly detection, priority evaluation,
risk scoring, and decision support.
"""
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.order import Order, OrderPriority
from app.schemas.order_schema import OrderAgentAnalysis


class OrderAgent:
    """
    Intelligent Agent for Order Processing and Quality Assessment.
    Operates heuristically or utilizes LLM reasoning when configured.
    """

    def __init__(self):
        self.llm_enabled = bool(settings.ENABLE_LLM_AGENT and settings.OPENAI_API_KEY)

    def analyze_order(self, db: Session, order: Order) -> OrderAgentAnalysis:
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
        for item in order.items:
            total_units += item.quantity
            if item.product:
                total_weight += item.product.weight_kg * item.quantity
                total_volume += item.product.volume_m3 * item.quantity
                if item.product.is_perishable or item.product.requires_cold_chain:
                    cold_chain_required = True

            # Quantity anomaly check
            if item.quantity > 500:
                anomalies.append(f"Unusually large volume for item (Product ID {item.product_id}: {item.quantity} units).")
                risk_score += 0.2

        if order.total_amount > settings.HIGH_VALUE_ORDER_THRESHOLD:
            anomalies.append(f"High-value order (${order.total_amount:,.2f}) exceeding threshold (${settings.HIGH_VALUE_ORDER_THRESHOLD:,.2f}).")
            risk_score += 0.15

        # Priority reasoning
        distributor_tier = order.distributor.tier.upper() if order.distributor and order.distributor.tier else "STANDARD"
        recommended_priority = OrderPriority.NORMAL.value

        if distributor_tier in ("VIP", "GOLD") or cold_chain_required:
            recommended_priority = OrderPriority.HIGH.value
        if cold_chain_required and distributor_tier == "VIP":
            recommended_priority = OrderPriority.URGENT.value

        # Calculate final risk score clamped to [0.0, 1.0]
        risk_score = min(round(risk_score, 2), 1.0)
        is_valid = (risk_score < 0.7) and (len(order.items) > 0)

        # Recommendation narrative
        if self.llm_enabled:
            recommendation = self._generate_llm_reasoning(order, anomalies, risk_score)
        else:
            recommendation = self._generate_heuristic_reasoning(
                order, distributor_tier, anomalies, cold_chain_required, risk_score
            )

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

    def _generate_heuristic_reasoning(
        self,
        order: Order,
        tier: str,
        anomalies: List[str],
        cold_chain: bool,
        risk: float
    ) -> str:
        lines = [
            f"Order {order.order_number} analyzed for Distributor '{order.distributor.name if order.distributor else 'N/A'}' (Tier: {tier}).",
            f"Risk Level: {'HIGH' if risk >= 0.5 else 'LOW' if risk <= 0.2 else 'MODERATE'} ({risk})."
        ]
        if cold_chain:
            lines.append("Perishable cargo identified: Reefer vehicle and expedited dispatch required.")
        if anomalies:
            lines.append(f"Attention flags: {'; '.join(anomalies)}")
        else:
            lines.append("Order parameters verified compliant with standard distribution thresholds.")
        return " ".join(lines)

    def _generate_llm_reasoning(self, order: Order, anomalies: List[str], risk: float) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            prompt = (
                f"You are an AI Logistics Order Specialist. Evaluate this order:\n"
                f"Order Number: {order.order_number}, Amount: ${order.total_amount}, Weight: {order.total_weight_kg}kg.\n"
                f"Anomalies: {anomalies}, Risk Score: {risk}.\n"
                f"Provide a concise 2-sentence operational recommendation."
            )
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return self._generate_heuristic_reasoning(
                order,
                order.distributor.tier if order.distributor else "STANDARD",
                anomalies,
                False,
                risk
            )


order_agent = OrderAgent()
