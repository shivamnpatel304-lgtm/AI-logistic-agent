"""
Reasoning Engines implementing Abstraction and Polymorphism.
Applies:
- Abstraction: Abstract ReasoningEngine defines the contract for intelligent decision support.
- Inheritance: HeuristicReasoningEngine and LLMReasoningEngine inherit from ReasoningEngine.
- Polymorphism: Agents can evaluate context and generate decisions using interchangeable reasoning backends.
- Encapsulation: API credentials, prompts, and heuristic threshold parsing are protected within engine classes.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.core.config import settings


class ReasoningEngine(ABC):
    """
    Abstract contract for decision-support reasoning engines.
    """

    @abstractmethod
    def reason(self, context: Dict[str, Any]) -> str:
        """Generates domain decision narrative from structured evaluation context."""
        pass


class HeuristicReasoningEngine(ReasoningEngine):
    """
    Deterministic rule-based reasoning engine. High speed, predictable, zero external dependencies.
    """

    def reason(self, context: Dict[str, Any]) -> str:
        order_number = context.get("order_number", "N/A")
        client_name = context.get("client_name", "N/A")
        client_tier = context.get("client_tier", "STANDARD")
        risk_score = context.get("risk_score", 0.0)
        cold_chain = context.get("cold_chain_required", False)
        anomalies = context.get("anomalies", [])

        risk_level = "HIGH" if risk_score >= 0.5 else "LOW" if risk_score <= 0.2 else "MODERATE"

        lines = [
            f"Order {order_number} analyzed for Distributor '{client_name}' (Tier: {client_tier}).",
            f"Risk Level: {risk_level} ({risk_score}).",
        ]

        if cold_chain:
            lines.append("Perishable cargo identified: Reefer vehicle and expedited dispatch required.")
        if anomalies:
            lines.append(f"Attention flags: {'; '.join(anomalies)}")
        else:
            lines.append("Order parameters verified compliant with standard distribution thresholds.")

        return " ".join(lines)


class LLMReasoningEngine(ReasoningEngine):
    """
    GenAI-powered reasoning engine utilizing OpenAI models with heuristic fallback.
    """

    def __init__(self, model_name: str = None, api_key: str = None):
        self._model_name = model_name or settings.OPENAI_MODEL
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._fallback_engine = HeuristicReasoningEngine()

    def reason(self, context: Dict[str, Any]) -> str:
        if not self._api_key:
            return self._fallback_engine.reason(context)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self._api_key)
            prompt = (
                f"You are an AI Logistics Order Specialist. Evaluate this order:\n"
                f"Order Number: {context.get('order_number')}, Amount: ${context.get('total_amount')}, "
                f"Weight: {context.get('total_weight_kg')}kg, Cold-Chain: {context.get('cold_chain_required')}.\n"
                f"Anomalies: {context.get('anomalies')}, Risk Score: {context.get('risk_score')}.\n"
                f"Provide a concise 2-sentence operational recommendation."
            )
            response = client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return self._fallback_engine.reason(context)


class ReasoningEngineFactory:
    """
    Factory creating appropriate reasoning engines based on system environment.
    """

    @staticmethod
    def create(prefer_llm: bool = True) -> ReasoningEngine:
        if prefer_llm and settings.ENABLE_LLM_AGENT and settings.OPENAI_API_KEY:
            return LLMReasoningEngine()
        return HeuristicReasoningEngine()
