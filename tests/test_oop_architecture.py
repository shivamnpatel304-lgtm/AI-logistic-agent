"""
Automated Test Suite Validating the 4 Pillars of OOP:
1. Encapsulation
2. Abstraction
3. Inheritance
4. Polymorphism
Also verifies End-to-End System Integrity and API Backward Compatibility.
"""
import unittest
from abc import ABC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

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
    DistanceCalculator,
    AbstractAllocationStrategy,
    SingleSourceAllocationStrategy,
    MultiNodeProximityAllocationStrategy,
    AllocationStrategyFactory,
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
from app.main import app


class TestOOPArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an in-memory SQLite database for testing
        cls.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.db = self.Session()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    # =========================================================================
    # PILLAR 1: ENCAPSULATION
    # =========================================================================
    def test_encapsulation_base_entity_serialization(self):
        prod = Product(
            sku="SKU-TEST-001",
            name="Test Product",
            unit_price=25.5,
            weight_kg=2.0,
            volume_m3=0.01,
        )
        self.db.add(prod)
        self.db.commit()

        d = prod.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["sku"], "SKU-TEST-001")
        self.assertIn("created_at", d)

    def test_encapsulation_product_cargo_metrics(self):
        prod = Product(
            sku="SKU-CHILL-01",
            name="Frozen Ice Cream",
            unit_price=10.0,
            weight_kg=1.5,
            volume_m3=0.005,
            is_perishable=True,
        )
        self.assertTrue(prod.is_temperature_controlled)
        metrics = prod.compute_bulk_metrics(10)
        self.assertEqual(metrics["total_weight_kg"], 15.0)
        self.assertEqual(metrics["total_price"], 100.0)
        self.assertTrue(metrics["requires_reefer"])

    def test_encapsulation_warehouse_capacity_invariants(self):
        wh = Warehouse(
            code="WH-ENC-01",
            name="Encapsulation Warehouse",
            address="123 Storage Rd",
            latitude=37.77,
            longitude=-122.41,
            capacity_m3=500.0,
            current_utilization=100.0,
        )
        self.assertEqual(wh.available_capacity_m3, 400.0)
        self.assertEqual(wh.utilization_percentage, 20.0)
        self.assertTrue(wh.can_accommodate_volume(300.0))
        self.assertFalse(wh.can_accommodate_volume(450.0))

        wh.record_utilization(50.0)
        self.assertEqual(wh.current_utilization, 150.0)

    def test_encapsulation_inventory_state_and_transactions(self):
        inv = Inventory(
            warehouse_id=1,
            product_id=1,
            quantity=100,
            reserved_quantity=20,
            safety_stock=30,
            reorder_point=15,
        )
        self.assertEqual(inv.available_quantity, 80)
        self.assertEqual(inv.stock_status, "OPTIMAL")

        # Reserve
        self.assertTrue(inv.reserve(30))
        self.assertEqual(inv.reserved_quantity, 50)
        self.assertEqual(inv.available_quantity, 50)

        # Fail over-reserve
        self.assertFalse(inv.reserve(60))

        # Release
        self.assertTrue(inv.release(10))
        self.assertEqual(inv.reserved_quantity, 40)

        # Deduct
        self.assertTrue(inv.deduct(20))
        self.assertEqual(inv.quantity, 80)
        self.assertEqual(inv.reserved_quantity, 20)

    def test_encapsulation_order_state_machine(self):
        order = Order(
            order_number="ORD-STATE-001",
            distributor_id=1,
            customer_name="Client Test",
            delivery_address="123 Test Ave",
            delivery_latitude=34.05,
            delivery_longitude=-118.24,
            status=OrderStatus.PENDING.value,
        )
        self.assertTrue(order.is_cancellable)
        self.assertTrue(order.can_transition_to(OrderStatus.ALLOCATED))

        # Valid transition
        order.transition_to(OrderStatus.ALLOCATED)
        self.assertEqual(order.status, OrderStatus.ALLOCATED.value)

        # Valid dispatch
        order.transition_to(OrderStatus.DISPATCHED)
        self.assertEqual(order.status, OrderStatus.DISPATCHED.value)
        self.assertFalse(order.is_cancellable)

        # Illegal transition from DISPATCHED to CANCELLED raises ValueError
        with self.assertRaises(ValueError):
            order.transition_to(OrderStatus.CANCELLED)

    def test_encapsulation_vehicle_capacity_checks(self):
        veh = Vehicle(
            plate_number="ENC-REEFER-01",
            vehicle_type=VehicleType.REEFER.value,
            max_weight_capacity_kg=2000.0,
            max_volume_capacity_m3=20.0,
            current_status=VehicleStatus.AVAILABLE.value,
        )
        self.assertTrue(veh.is_available)
        self.assertTrue(veh.is_reefer)
        self.assertTrue(veh.can_accommodate(1500.0, 10.0, requires_reefer=True))
        self.assertFalse(veh.can_accommodate(2500.0, 10.0, requires_reefer=True))

        veh.assign()
        self.assertEqual(veh.current_status, VehicleStatus.ASSIGNED.value)
        self.assertFalse(veh.is_available)

    # =========================================================================
    # PILLAR 2: ABSTRACTION
    # =========================================================================
    def test_abstraction_base_agent_cannot_be_instantiated(self):
        """Verify that BaseAgent is an ABC and cannot be directly instantiated."""
        with self.assertRaises(TypeError):
            BaseAgent(name="AbstractAgent", description="Test", agent_type="TEST")

    def test_abstraction_strategy_cannot_be_instantiated(self):
        """Verify that AbstractAllocationStrategy cannot be directly instantiated."""
        with self.assertRaises(TypeError):
            AbstractAllocationStrategy()

    def test_abstraction_reasoning_engine_cannot_be_instantiated(self):
        """Verify that ReasoningEngine is an ABC and requires implementation."""
        with self.assertRaises(TypeError):
            ReasoningEngine()

    # =========================================================================
    # PILLAR 3: INHERITANCE
    # =========================================================================
    def test_inheritance_models_inherit_base_entity(self):
        self.assertTrue(issubclass(Order, BaseEntity))
        self.assertTrue(issubclass(OrderItem, BaseEntity))
        self.assertTrue(issubclass(Product, BaseEntity))
        self.assertTrue(issubclass(Warehouse, BaseEntity))
        self.assertTrue(issubclass(Distributor, BaseEntity))
        self.assertTrue(issubclass(Inventory, BaseEntity))
        self.assertTrue(issubclass(Vehicle, BaseEntity))

    def test_inheritance_agents_inherit_base_agent(self):
        self.assertTrue(issubclass(OrderAgent, BaseAgent))
        self.assertTrue(issubclass(InventoryAgent, BaseAgent))
        self.assertTrue(issubclass(AllocationAgent, BaseAgent))
        self.assertTrue(issubclass(LogisticsAgent, BaseAgent))

    def test_inheritance_services_inherit_base_service(self):
        self.assertTrue(issubclass(OrderService, BaseService))
        self.assertTrue(issubclass(ProductService, BaseService))
        self.assertTrue(issubclass(WarehouseService, BaseService))
        self.assertTrue(issubclass(InventoryService, BaseService))
        self.assertTrue(issubclass(LogisticsService, BaseService))

    def test_inheritance_allocation_strategies_inherit_abstract_strategy(self):
        self.assertTrue(issubclass(SingleSourceAllocationStrategy, AbstractAllocationStrategy))
        self.assertTrue(issubclass(MultiNodeProximityAllocationStrategy, AbstractAllocationStrategy))

    def test_inheritance_reasoning_engines(self):
        self.assertTrue(issubclass(HeuristicReasoningEngine, ReasoningEngine))
        self.assertTrue(issubclass(LLMReasoningEngine, ReasoningEngine))

    # =========================================================================
    # PILLAR 4: POLYMORPHISM
    # =========================================================================
    def test_polymorphism_agent_orchestrator(self):
        """
        Verify that heterogeneous agent instances can be held and executed
        polymorphically through the common BaseAgent interface.
        """
        orch = AgentOrchestrator([
            order_agent,
            inventory_agent,
            allocation_agent,
            logistics_agent,
        ])
        health = orch.get_system_health()
        self.assertEqual(health["total_agents"], 4)
        for agent_stat in health["agents"]:
            self.assertIn("agent_name", agent_stat)
            self.assertEqual(agent_stat["status"], "HEALTHY")

    def test_polymorphism_allocation_strategies(self):
        """
        Verify that different allocation strategies implement the same allocate() interface.
        """
        strategy1: AbstractAllocationStrategy = AllocationStrategyFactory.create(prefer_single_warehouse=True)
        strategy2: AbstractAllocationStrategy = AllocationStrategyFactory.create(prefer_single_warehouse=False)

        self.assertIsInstance(strategy1, SingleSourceAllocationStrategy)
        self.assertIsInstance(strategy2, MultiNodeProximityAllocationStrategy)

    def test_polymorphism_reasoning_engines(self):
        """
        Verify that different reasoning engines can be evaluated interchangeably.
        """
        engines: list[ReasoningEngine] = [
            HeuristicReasoningEngine(),
            LLMReasoningEngine(api_key=""),  # falls back to heuristic safely
        ]
        context = {
            "order_number": "ORD-POLY-01",
            "client_name": "Acme Corp",
            "client_tier": "GOLD",
            "total_amount": 500.0,
            "total_weight_kg": 50.0,
            "cold_chain_required": True,
            "risk_score": 0.1,
            "anomalies": [],
        }
        for eng in engines:
            narrative = eng.reason(context)
            self.assertIsInstance(narrative, str)
            self.assertIn("ORD-POLY-01", narrative)

    # =========================================================================
    # SYSTEM & API INTEGRATION TEST
    # =========================================================================
    def test_api_health_endpoint(self):
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("agents", data)
        self.assertEqual(data["agents"]["total_agents"], 4)

    def test_api_root_endpoint_metadata(self):
        client = TestClient(app)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("oop_architecture", data)
        self.assertIn("encapsulation", data["oop_architecture"])
        self.assertIn("abstraction", data["oop_architecture"])
        self.assertIn("inheritance", data["oop_architecture"])
        self.assertIn("polymorphism", data["oop_architecture"])

    def test_end_to_end_fulfillment_pipeline(self):
        # 1. Setup Distributor
        dist = Distributor(
            code="DIST-E2E-01",
            name="Alpha Logistics Partner",
            contact_email="alpha@logistics.com",
            address="100 Highway Rd",
            latitude=37.7749,
            longitude=-122.4194,
            tier="VIP",
        )
        self.db.add(dist)

        # 2. Setup Warehouse
        wh = Warehouse(
            code="WH-E2E-01",
            name="Bay Hub",
            address="200 Warehouse Way",
            latitude=37.7800,
            longitude=-122.4100,
            capacity_m3=1000.0,
            current_utilization=50.0,
            is_active=True,
        )
        self.db.add(wh)
        self.db.commit()

        # 3. Setup Product & Inventory
        prod = Product(
            sku="SKU-E2E-CHILL",
            name="Perishable Goods",
            unit_price=50.0,
            weight_kg=5.0,
            volume_m3=0.02,
            is_perishable=True,
        )
        self.db.add(prod)
        self.db.commit()

        inv = Inventory(
            warehouse_id=wh.id,
            product_id=prod.id,
            quantity=100,
            reserved_quantity=0,
            safety_stock=20,
            reorder_point=10,
        )
        self.db.add(inv)

        # 4. Setup Fleet Vehicle
        veh = Vehicle(
            plate_number="REEFER-E2E-99",
            vehicle_type=VehicleType.REEFER.value,
            max_weight_capacity_kg=5000.0,
            max_volume_capacity_m3=50.0,
            current_status=VehicleStatus.AVAILABLE.value,
            warehouse_id=wh.id,
        )
        self.db.add(veh)
        self.db.commit()

        # 5. Create Order
        order = Order(
            order_number="ORD-E2E-001",
            distributor_id=dist.id,
            customer_name="SuperMart Inc",
            delivery_address="300 Market St",
            delivery_latitude=37.7900,
            delivery_longitude=-122.4000,
            status=OrderStatus.PENDING.value,
            priority=OrderPriority.NORMAL.value,
            total_amount=500.0,
            total_weight_kg=50.0,
            items=[
                OrderItem(
                    product_id=prod.id,
                    quantity=10,
                    unit_price=50.0,
                )
            ],
        )
        self.db.add(order)
        self.db.commit()

        # 6. Execute End-to-End Multi-Agent Pipeline via Orchestrator
        orch = AgentOrchestrator([order_agent, allocation_agent, logistics_agent])
        result = orch.run_end_to_end_pipeline(self.db, order_id=order.id)

        self.assertEqual(result["pipeline_status"], "COMPLETED")
        self.assertIn("order_analysis", result["stages"])
        self.assertIn("allocation_result", result["stages"])
        self.assertIn("dispatch_recommendation", result["stages"])

        # Verify Stage 1 (Order Analysis & Priority Escalation)
        analysis = result["stages"]["order_analysis"]
        self.assertTrue(analysis.cold_chain_required)
        self.assertEqual(analysis.recommended_priority, OrderPriority.URGENT.value)

        # Verify Stage 2 (Allocation)
        allocation = result["stages"]["allocation_result"]
        self.assertTrue(allocation.is_fully_allocated)
        self.assertEqual(len(allocation.fulfillment_centers), 1)

        # Verify Stage 3 (Dispatch Recommendation)
        dispatch = result["stages"]["dispatch_recommendation"]
        self.assertEqual(dispatch.vehicle_type, VehicleType.REEFER.value)
        self.assertTrue(dispatch.requires_reefer)
        self.assertEqual(dispatch.assigned_vehicle_id, veh.id)


if __name__ == "__main__":
    unittest.main()
