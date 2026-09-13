"""
Demo Script: Executing all 4 Pillars of OOP across AI Logistics Agent.
Demonstrates:
1. Encapsulation in action
2. Abstraction in action
3. Inheritance in action
4. Polymorphism in action
5. Full Autonomous Multi-Agent Logistics Pipeline
"""
import sys
import io

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.models.base import BaseEntity
from app.models.order import Order, OrderItem, OrderStatus, OrderPriority
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.distributor import Distributor
from app.models.inventory import Inventory
from app.models.vehicle import Vehicle, VehicleType, VehicleStatus

from app.services.base_service import BaseService
from app.services.order_service import OrderService, order_service
from app.services.inventory_service import InventoryService, ProductService, WarehouseService
from app.services.allocation_strategies import (
    AbstractAllocationStrategy,
    SingleSourceAllocationStrategy,
    MultiNodeProximityAllocationStrategy,
    AllocationStrategyFactory,
    DistanceCalculator,
)
from app.services.allocation_service import AllocationService, allocation_service
from app.services.logistics_service import LogisticsService, logistics_service

from app.agents.base_agent import BaseAgent
from app.agents.reasoning import (
    ReasoningEngine,
    HeuristicReasoningEngine,
    LLMReasoningEngine,
)
from app.agents.order_agent import OrderAgent, order_agent
from app.agents.inventory_agent import InventoryAgent, inventory_agent
from app.agents.allocation_agent import AllocationAgent, allocation_agent
from app.agents.logistics_agent import LogisticsAgent, logistics_agent
from app.agents.orchestrator import AgentOrchestrator, orchestrator


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title.upper()}")
    print("=" * 70)


def run_oop_demonstration():
    print_header("Initializing In-Memory Database for OOP Showcase")
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    print("Database tables initialized successfully.")

    # =========================================================================
    # PILLAR 1: ENCAPSULATION
    # =========================================================================
    print_header("Pillar 1: Encapsulation (State Invariants & Domain Methods)")

    # 1. Product Encapsulation
    prod = Product(
        sku="MED-VACCINE-01",
        name="Temperature-Sensitive Vaccine",
        unit_price=120.0,
        weight_kg=0.5,
        volume_m3=0.002,
        requires_cold_chain=True,
    )
    db.add(prod)
    db.commit()
    print(f"[Encapsulated Product] '{prod.name}'")
    print(f"  - Requires Temperature Control (@property): {prod.is_temperature_controlled}")
    bulk = prod.compute_bulk_metrics(50)
    print(f"  - Bulk Metrics for 50 units (Encapsulated Method): {bulk}")

    # 2. Warehouse Encapsulation
    wh = Warehouse(
        code="WH-NORTH-01",
        name="North Regional Fulfillment Center",
        address="100 Logistics Blvd, Seattle, WA",
        latitude=47.6062,
        longitude=-122.3321,
        capacity_m3=2000.0,
        current_utilization=400.0,
        is_active=True,
    )
    db.add(wh)
    db.commit()
    print(f"\n[Encapsulated Warehouse] '{wh.name}'")
    print(f"  - Available Capacity (@property): {wh.available_capacity_m3} m3")
    print(f"  - Utilization Rate (@property): {wh.utilization_percentage}%")
    print(f"  - Can fit 1200 m3 cargo? {wh.can_accommodate_volume(1200.0)}")
    print(f"  - Can fit 1800 m3 cargo? {wh.can_accommodate_volume(1800.0)}")

    # 3. Inventory Encapsulation (Atomic Transactions on Entity)
    inv = Inventory(
        warehouse_id=wh.id,
        product_id=prod.id,
        quantity=200,
        reserved_quantity=0,
        safety_stock=30,
        reorder_point=15,
    )
    db.add(inv)
    db.commit()
    print(f"\n[Encapsulated Inventory] Warehouse: {wh.code}, Product: {prod.sku}")
    print(f"  - On Hand: {inv.quantity}, Available: {inv.available_quantity}, Status: {inv.stock_status}")
    inv.reserve(40)
    print(f"  - After inv.reserve(40) -> Reserved: {inv.reserved_quantity}, Available: {inv.available_quantity}")
    inv.release(10)
    print(f"  - After inv.release(10) -> Reserved: {inv.reserved_quantity}, Available: {inv.available_quantity}")
    inv.deduct(15)
    print(f"  - After inv.deduct(15)  -> Total: {inv.quantity}, Reserved: {inv.reserved_quantity}, Available: {inv.available_quantity}")

    # 4. Order State Machine Encapsulation
    dist = Distributor(
        code="DIST-HEALTH-01",
        name="Metro Health Network",
        contact_email="supplies@metrohealth.org",
        address="500 Medical Center Way",
        latitude=47.6101,
        longitude=-122.3421,
        tier="VIP",
    )
    db.add(dist)
    db.commit()

    order = Order(
        order_number="ORD-DEMO-2026",
        distributor_id=dist.id,
        customer_name="St. Jude Hospital",
        delivery_address="777 Hope St, Seattle, WA",
        delivery_latitude=47.6150,
        delivery_longitude=-122.3350,
        status=OrderStatus.PENDING.value,
        items=[OrderItem(product_id=prod.id, quantity=25, unit_price=120.0)],
    )
    db.add(order)
    db.commit()
    print(f"\n[Encapsulated Order Lifecycle] Order: {order.order_number}")
    print(f"  - Initial Status: {order.status}, Cancellable: {order.is_cancellable}")
    order.transition_to(OrderStatus.ALLOCATED)
    print(f"  - Valid transition: order.transition_to(ALLOCATED) -> {order.status}")
    order.transition_to(OrderStatus.DISPATCHED)
    print(f"  - Valid transition: order.transition_to(DISPATCHED) -> {order.status}")
    print(f"  - Cancellable once Dispatched? {order.is_cancellable}")
    try:
        order.transition_to(OrderStatus.CANCELLED)
    except ValueError as e:
        print(f"  - Protected Invariant: Illegal transition blocked with ValueError: \"{e}\"")

    # 5. Vehicle Encapsulation
    veh = Vehicle(
        plate_number="WA-REEFER-77",
        vehicle_type=VehicleType.REEFER.value,
        max_weight_capacity_kg=3000.0,
        max_volume_capacity_m3=25.0,
        warehouse_id=wh.id,
    )
    db.add(veh)
    db.commit()
    print(f"\n[Encapsulated Vehicle] Plate: {veh.plate_number}, Type: {veh.vehicle_type}")
    print(f"  - Is Reefer (@property): {veh.is_reefer}")
    print(f"  - Can carry 2500kg refrigerated? {veh.can_accommodate(2500.0, 10.0, requires_reefer=True)}")
    print(f"  - Can carry 3500kg refrigerated? {veh.can_accommodate(3500.0, 10.0, requires_reefer=True)}")

    # =========================================================================
    # PILLAR 2: ABSTRACTION
    # =========================================================================
    print_header("Pillar 2: Abstraction (Abstract Contracts & Base Classes)")
    print("[Abstract Base Classes]")
    print(f"  - BaseAgent is abstract: {hasattr(BaseAgent, '__abstractmethods__')}")
    print(f"    Abstract methods enforced: {list(BaseAgent.__abstractmethods__)}")
    print(f"  - AbstractAllocationStrategy is abstract: {hasattr(AbstractAllocationStrategy, '__abstractmethods__')}")
    print(f"    Abstract methods enforced: {list(AbstractAllocationStrategy.__abstractmethods__)}")
    print(f"  - ReasoningEngine is abstract: {hasattr(ReasoningEngine, '__abstractmethods__')}")
    print(f"    Abstract methods enforced: {list(ReasoningEngine.__abstractmethods__)}")

    try:
        BaseAgent("Dummy", "Desc", "TYPE")
    except TypeError as te:
        print(f"  - Direct instantiation blocked: \"{te}\"")

    # =========================================================================
    # PILLAR 3: INHERITANCE
    # =========================================================================
    print_header("Pillar 3: Inheritance (Hierarchies & Shared Capabilities)")
    print("[Model Inheritance from BaseEntity]")
    for model in [Order, OrderItem, Product, Warehouse, Distributor, Inventory, Vehicle]:
        print(f"  - {model.__name__:<15} -> Subclass of BaseEntity: {issubclass(model, BaseEntity)}")

    print("\n[Service Inheritance from BaseService[T]]")
    for srv in [OrderService, ProductService, WarehouseService, InventoryService, LogisticsService]:
        print(f"  - {srv.__name__:<18} -> Subclass of BaseService: {issubclass(srv, BaseService)}")

    print("\n[Agent Inheritance from BaseAgent]")
    for ag in [OrderAgent, InventoryAgent, AllocationAgent, LogisticsAgent]:
        print(f"  - {ag.__name__:<18} -> Subclass of BaseAgent: {issubclass(ag, BaseAgent)}")

    # =========================================================================
    # PILLAR 4: POLYMORPHISM
    # =========================================================================
    print_header("Pillar 4: Polymorphism (Interchangeable Execution & Strategies)")

    # 1. Strategy Pattern Polymorphism
    print("[1. Sourcing Strategy Polymorphism]")
    strat_single = AllocationStrategyFactory.create(prefer_single_warehouse=True)
    strat_multi = AllocationStrategyFactory.create(prefer_single_warehouse=False)
    print(f"  - Prefer Single = True  -> Created: {strat_single.__class__.__name__}")
    print(f"  - Prefer Single = False -> Created: {strat_multi.__class__.__name__}")
    print(f"  - Both share same .allocate() signature: {hasattr(strat_single, 'allocate') and hasattr(strat_multi, 'allocate')}")

    # 2. Reasoning Engine Polymorphism
    print("\n[2. Reasoning Engine Polymorphism]")
    engines = [HeuristicReasoningEngine(), LLMReasoningEngine()]
    test_context = {
        "order_number": "ORD-POLY-99",
        "client_name": dist.name,
        "client_tier": dist.tier,
        "risk_score": 0.15,
        "cold_chain_required": True,
        "anomalies": [],
    }
    for eng in engines:
        explanation = eng.reason(test_context)
        print(f"  - Engine [{eng.__class__.__name__}]:\n    \"{explanation}\"")

    # 3. Agent Orchestration Polymorphism
    print("\n[3. Multi-Agent Orchestrator Polymorphism]")
    multi_agents: list[BaseAgent] = [order_agent, inventory_agent, allocation_agent, logistics_agent]
    print(f"  - Iterating over {len(multi_agents)} heterogeneous agents via BaseAgent contract:")
    for ag in multi_agents:
        health = ag.get_health_status()
        print(f"    * {ag.name:<28} | Type: {ag.agent_type:<22} | Status: {health['status']}")

    # =========================================================================
    # END-TO-END AUTONOMOUS MULTI-AGENT PIPELINE
    # =========================================================================
    print_header("Autonomous Multi-Agent Pipeline Execution")
    
    # Create fresh unallocated order for full pipeline demo
    pipeline_order = Order(
        order_number="ORD-PIPELINE-2026",
        distributor_id=dist.id,
        customer_name="Regional Emergency Center",
        delivery_address="999 Downtown Way, Seattle, WA",
        delivery_latitude=47.6080,
        delivery_longitude=-122.3350,
        status=OrderStatus.PENDING.value,
        priority=OrderPriority.NORMAL.value,
        items=[
            OrderItem(
                product_id=prod.id,
                quantity=30,
                unit_price=prod.unit_price,
            )
        ],
    )
    pipeline_order.recalculate_metrics()
    db.add(pipeline_order)
    db.commit()

    print(f"Order Created: #{pipeline_order.order_number} (${pipeline_order.total_amount:,.2f})")

    # Run full multi-agent pipeline through orchestrator
    pipeline_orch = AgentOrchestrator([order_agent, allocation_agent, logistics_agent])
    results = pipeline_orch.run_end_to_end_pipeline(db, order_id=pipeline_order.id)

    print("\n--- Pipeline Execution Summary ---")
    print(f"Pipeline Status: {results['pipeline_status']}")

    analysis = results["stages"]["order_analysis"]
    print(f"\n[Stage 1: Order Validation Agent]")
    print(f"  - Priority Escalated: {analysis.recommended_priority}")
    print(f"  - Cold Chain Detected: {analysis.cold_chain_required}")
    print(f"  - AI Recommendation: {analysis.ai_recommendation}")

    allocation = results["stages"]["allocation_result"]
    print(f"\n[Stage 2: Sourcing Allocation Agent]")
    print(f"  - Fully Allocated: {allocation.is_fully_allocated}")
    print(f"  - Fulfillment Center(s): {allocation.fulfillment_centers}")
    print(f"  - Strategy Notes: {allocation.optimization_notes}")

    dispatch = results["stages"]["dispatch_recommendation"]
    print(f"\n[Stage 3: Fleet Logistics Agent]")
    print(f"  - Matched Vehicle: {dispatch.vehicle_plate} ({dispatch.vehicle_type})")
    print(f"  - Reefer Verified: {dispatch.requires_reefer}")
    print(f"  - Est. Distance: {dispatch.estimated_distance_km} km | ETA: {dispatch.estimated_transit_hours} hrs")
    print(f"  - Dispatch Advisory: {dispatch.dispatch_notes}")

    print_header("All 4 OOP Pillars Executed Successfully with Zero Errors")


if __name__ == "__main__":
    run_oop_demonstration()
