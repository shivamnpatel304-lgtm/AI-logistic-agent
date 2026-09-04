"""
Agents module initialization
Exports all AI agent instances.
"""
from app.agents.order_agent import OrderAgent, order_agent
from app.agents.inventory_agent import InventoryAgent, inventory_agent
from app.agents.allocation_agent import AllocationAgent, allocation_agent
from app.agents.logistics_agent import LogisticsAgent, logistics_agent

__all__ = [
    "OrderAgent",
    "order_agent",
    "InventoryAgent",
    "inventory_agent",
    "AllocationAgent",
    "allocation_agent",
    "LogisticsAgent",
    "logistics_agent",
]
