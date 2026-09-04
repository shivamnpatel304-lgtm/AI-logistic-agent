"""
AI Inventory Agent:
Monitors real-time stock levels, detects critical stockouts,
generates inventory rebalancing recommendations, and optimizes safety stock.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.inventory import Inventory
from app.models.warehouse import Warehouse
from app.models.product import Product
from app.schemas.inventory_schema import LowStockAlert, RebalanceRecommendation
from app.services.inventory_service import get_stock_alerts
from app.services.allocation_service import generate_rebalance_recommendations


class InventoryAgent:
    """
    Intelligent Agent for Multi-Warehouse Inventory Health and Optimization.
    """

    def __init__(self):
        self.llm_enabled = bool(settings.ENABLE_LLM_AGENT and settings.OPENAI_API_KEY)

    def assess_network_health(self, db: Session) -> Dict[str, Any]:
        """
        Calculates an overall health scorecard of the warehouse inventory network.
        """
        inventories = db.query(Inventory).all()
        warehouses = db.query(Warehouse).filter(Warehouse.is_active.is_(True)).all()
        products = db.query(Product).all()

        total_skus = len(products)
        total_warehouses = len(warehouses)
        total_stock = sum(inv.quantity for inv in inventories)
        total_reserved = sum(inv.reserved_quantity for inv in inventories)

        alerts = get_stock_alerts(db)
        rebalances = generate_rebalance_recommendations(db)

        critical_count = sum(1 for a in alerts if a.status == "CRITICAL")
        low_count = sum(1 for a in alerts if a.status == "LOW")

        health_score = 100.0
        health_score -= (critical_count * 15.0)
        health_score -= (low_count * 5.0)
        health_score = max(0.0, min(100.0, health_score))

        health_status = "EXCELLENT" if health_score >= 85 else "GOOD" if health_score >= 70 else "NEEDS_ATTENTION" if health_score >= 50 else "CRITICAL"

        insights = self._generate_insights(
            health_score, health_status, critical_count, low_count, len(rebalances), total_stock
        )

        return {
            "health_score": health_score,
            "status": health_status,
            "total_warehouses": total_warehouses,
            "total_products": total_skus,
            "total_units_on_hand": total_stock,
            "total_units_reserved": total_reserved,
            "critical_stockout_alerts": critical_count,
            "low_stock_warnings": low_count,
            "pending_rebalance_opportunities": len(rebalances),
            "stock_alerts": alerts,
            "rebalance_recommendations": rebalances,
            "agent_insights": insights,
        }

    def _generate_insights(
        self, score: float, status: str, critical: int, low: int, rebalance_count: int, total_stock: int
    ) -> str:
        if critical > 0:
            return (
                f"Urgent attention required: {critical} product line(s) below reorder threshold. "
                f"{rebalance_count} inter-warehouse transfers identified to alleviate regional shortages."
            )
        if low > 0:
            return (
                f"Supply network stable ({score}/100 - {status}). {low} SKUs approaching safety stock; "
                f"rebalancing from surplus warehouses recommended before next procurement cycle."
            )
        return (
            f"Supply chain optimal ({score}/100 - {status}). All active warehouses maintained above safety thresholds "
            f"with {total_stock} total units readily available."
        )


inventory_agent = InventoryAgent()
