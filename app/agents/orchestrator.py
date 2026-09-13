"""
Agent Orchestrator demonstrating Polymorphic Multi-Agent Coordination.
Applies:
- Polymorphism: Treats all registered agents uniformly via the BaseAgent interface.
- Abstraction: Coordinates end-to-end multi-agent pipelines without coupling to concrete implementations.
- Encapsulation: Encapsulates agent discovery, execution auditing, and stage-by-stage pipeline state.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.agents.base_agent import BaseAgent
from app.agents.order_agent import order_agent
from app.agents.inventory_agent import inventory_agent
from app.agents.allocation_agent import allocation_agent
from app.agents.logistics_agent import logistics_agent


class AgentOrchestrator:
    """
    Multi-Agent Orchestrator managing heterogeneous agents polymorphically.
    """

    def __init__(self, agents: Optional[List[BaseAgent]] = None):
        self._agents: Dict[str, BaseAgent] = {}
        if agents:
            for agent in agents:
                self.register_agent(agent)

    def register_agent(self, agent: BaseAgent) -> None:
        """Registers a BaseAgent instance for orchestrated execution."""
        self._agents[agent.name.lower()] = agent

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name.lower())

    def get_all_agents(self) -> List[BaseAgent]:
        return list(self._agents.values())

    def get_system_health(self) -> Dict[str, Any]:
        """
        Polymorphically queries each registered agent's health status.
        """
        diagnostics = [agent.get_health_status() for agent in self._agents.values()]
        return {
            "total_agents": len(self._agents),
            "agents": diagnostics,
            "overall_status": "HEALTHY",
        }

    def execute_agent(self, agent_name: str, db: Session, **kwargs) -> Any:
        """
        Executes a registered agent polymorphically via the common run() method.
        """
        agent = self.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not registered in orchestrator.")
        return agent.run(db, **kwargs)

    def run_end_to_end_pipeline(
        self,
        db: Session,
        order_id: int,
        prefer_single_warehouse: bool = True,
    ) -> Dict[str, Any]:
        """
        Runs the full autonomous logistics pipeline for an order:
        Stage 1: Order Validation & Anomaly Analysis (OrderAgent)
        Stage 2: Network Inventory Allocation & Reservation (AllocationAgent)
        Stage 3: Fleet Matching & Dispatch Planning (LogisticsAgent)
        """
        order_agent_instance = self.get_agent("order quality agent")
        alloc_agent_instance = self.get_agent("sourcing & allocation agent")
        logistics_agent_instance = self.get_agent("fleet & dispatch agent")

        results = {}

        # Stage 1: Order Evaluation
        if order_agent_instance:
            analysis = order_agent_instance.run(db, order_id=order_id)
            results["order_analysis"] = analysis

        # Stage 2: Sourcing Allocation
        if alloc_agent_instance:
            allocation = alloc_agent_instance.run(
                db,
                order_id=order_id,
                prefer_single_warehouse=prefer_single_warehouse,
                execute_allocation=True,
            )
            results["allocation_result"] = allocation

        # Stage 3: Fleet Dispatch Plan
        if logistics_agent_instance:
            dispatch_plan = logistics_agent_instance.run(db, order_id=order_id)
            results["dispatch_recommendation"] = dispatch_plan

        return {
            "order_id": order_id,
            "pipeline_status": "COMPLETED",
            "stages": results,
        }


# Global orchestrator singleton initialized with all system agents
orchestrator = AgentOrchestrator([
    order_agent,
    inventory_agent,
    allocation_agent,
    logistics_agent,
])
