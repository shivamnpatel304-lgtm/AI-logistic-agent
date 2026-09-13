"""
Base Agent Abstract Class for Multi-Agent Logistics Architecture.
Applies:
- Abstraction: Defines abstract interface (run, get_health_status) for all AI agents.
- Inheritance: Subclasses inherit common telemetry, naming, and reasoning engine capabilities.
- Polymorphism: Orchestrators can uniformly execute .run() across heterogeneous agent types.
- Encapsulation: Protects internal reasoning configuration, error boundaries, and telemetry counters.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.agents.reasoning import ReasoningEngine, ReasoningEngineFactory


class BaseAgent(ABC):
    """
    Abstract Base Class for all autonomous logistics agents.
    Subclassed by OrderAgent, InventoryAgent, AllocationAgent, LogisticsAgent.
    """

    def __init__(
        self,
        name: str,
        description: str,
        agent_type: str,
        reasoning_engine: Optional[ReasoningEngine] = None,
    ):
        self._name = name
        self._description = description
        self._agent_type = agent_type
        self._reasoning_engine = reasoning_engine or ReasoningEngineFactory.create()
        self._execution_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def agent_type(self) -> str:
        return self._agent_type

    @property
    def execution_count(self) -> int:
        return self._execution_count

    @property
    def reasoning_engine(self) -> ReasoningEngine:
        return self._reasoning_engine

    def explain(self, context: Dict[str, Any]) -> str:
        """
        Delegates decision narrative generation to encapsulated reasoning engine.
        """
        return self._reasoning_engine.reason(context)

    def _increment_executions(self) -> None:
        """Internal telemetry counter."""
        self._execution_count += 1

    @abstractmethod
    def run(self, db: Session, **kwargs) -> Any:
        """
        Polymorphic execution entrypoint for all agents.
        Accepts database session and agent-specific keyword arguments.
        """
        pass

    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """
        Returns agent health, operational readiness, and execution diagnostics.
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self._name}', type='{self._agent_type}')>"
