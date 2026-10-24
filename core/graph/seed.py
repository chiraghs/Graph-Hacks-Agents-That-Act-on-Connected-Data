"""seed.py - High-speed, idempotent synthetic data generator for FalkorDB Supply Chain Graph.

Optimized for FalkorDB Cloud & Local Docker:
- Uses unified db.py connection helper
- Fully idempotent: purges existing graph before repopulating
- High-speed UNWIND query batching (minimizes network round-trips for Cloud latency)
- Plants all 4 benchmark hackathon scenarios (HARMFUL M7, HARMLESS M12, SPOF part, Benign noise)
"""

import sys
import random
from core.db import get_graph, get_connection_config
from core.graph.scoring import (
    compute_machine_risk,
    compute_demand_forecast,
    compute_safety_stock,
)

SEED = 42
random.seed(SEED)


def build_synthetic_dataset() -> Dict[str, Any]:
    """Generate all nodes and relationships deterministically."""
    rng = random.Random(SEED)

    # 1. Regions
    regions = [
        {"id": "REG_NA", "name": "North America"},
        {"id": "REG_EU", "name": "Europe"},
        {"id": "REG_EAST_ASIA", "name": "East Asia"},
        {"id": "REG_SE_ASIA", "name": "Southeast Asia"},
        {"id": "REG_LATAM", "name": "Latin America"},
    ]

    # 2. Plants (3 plants)
    plants = [
        {"id": "PLANT_DETROIT", "name": "Apex Advanced Assembly", "location": "Detroit, USA"},
        {"id": "PLANT_AUSTIN", "name": "Silicon Hill Precision", "location": "Austin, USA"},
        {"id": "PLANT_MUNICH", "name": "Bavaria Mechatronics", "location": "Munich, Germany"},
    ]

    # 3. Warehouses (6 warehouses)
    warehouses = [
        {"id": "WH_MIDWEST", "name": "Central Logistics Hub", "location": "Chicago, IL", "capacity": 25000},
        {"id": "WH_EAST_COAST", "name": "Atlantic Gateway", "location": "Newark, NJ", "capacity": 20000},
        {"id": "WH_WEST_COAST", "name": "Pacific Freight Terminal", "location": "Long Beach, CA", "capacity": 22000},
        {"id": "WH_SOUTH", "name": "Gulf Distribution Depot", "location": "Dallas, TX", "capacity": 18000},
        {"id": "WH_CENTRAL_EU", "name": "Rhine-Main Distribution", "location": "Frankfurt, Germany", "capacity": 30000},
        {"id": "WH_NORDIC", "name": "Nordic Fulfillment Center", "location": "Gothenburg, Sweden", "capacity": 15000},
    ]

    # 4. Customers (40 customers)
    customers = []
    for i in range(1, 41):
        c_id = f"CUST_{i:03d}"
        tier = "Strategic" if i <= 10 else ("Enterprise" if i <= 25 else "Standard")
        customers.append({
            "id": c_id,
            "name": f"Client Corp {i:02d}",
            "tier": tier,
        })

    # 5. Suppliers (15 suppliers)
    suppliers = [
        {"id": "SUPPLIER_01", "name": "Titanium Dynamics", "rating": 4.8, "region": "REG_NA"},
        {"id": "SUPPLIER_02", "name": "Vanguard Microelectronics", "rating": 4.6, "region": "REG_EAST_ASIA"},
        {"id": "SUPPLIER_03", "name": "EuroAlloy Casting GmbH", "rating": 4.7, "region": "REG_EU"},
        {"id": "SUPPLIER_04", "name": "Nippon Sensor Works", "rating": 4.9, "region": "REG_EAST_ASIA"},
        {"id": "SUPPLIER_05", "name": "Pacific Polymer Inc", "rating": 4.2, "region": "REG_SE_ASIA"},
        {"id": "SUPPLIER_06", "name": "Apex Fasteners & Seals", "rating": 4.5, "region": "REG_NA"},
        {"id": "SUPPLIER_07", "name": "Munich Precision Stamping", "rating": 4.8, "region": "REG_EU"},
        {"id": "SUPPLIER_08", "name": "Seoul Semiconductor Fab", "rating": 4.4, "region": "REG_EAST_ASIA"},
        {"id": "SUPPLIER_09", "name": "Global Wire & Harness", "rating": 4.1, "region": "REG_LATAM"},
        {"id": "SUPPLIER_10", "name": "Bavarian Bearing AG", "rating": 4.6, "region": "REG_EU"},
        {"id": "SUPPLIER_11", "name": "Kyoto Actuator Tech", "rating": 4.7, "region": "REG_EAST_ASIA"},
        {"id": "SUPPLIER_12", "name": "Texas Silicon Foundry", "rating": 4.5, "region": "REG_NA"},
        {"id": "SUPPLIER_13", "name": "Shenzhen Opto-Sensors", "rating": 4.3, "region": "REG_EAST_ASIA"},
        {"id": "SUPPLIER_ALT_M7", "name": "Express Emergency Foundry", "rating": 4.0, "region": "REG_NA"},
        {"id": "SUPPLIER_SOLO_SPOF", "name": "Monopoly Rare Alloys", "rating": 3.9, "region": "REG_EAST_ASIA"},
    ]

    alternate_suppliers = [
        {"s1": "SUPPLIER_01", "s2": "SUPPLIER_03"},
        {"s1": "SUPPLIER_02", "s2": "SUPPLIER_08"},
        {"s1": "SUPPLIER_04", "s2": "SUPPLIER_13"},
        {"s1": "SUPPLIER_06", "s2": "SUPPLIER_07"},
        {"s1": "SUPPLIER_10", "s2": "SUPPLIER_07"},
        {"s1": "SUPPLIER_01", "s2": "SUPPLIER_ALT_M7"},
    ]

    # 6. Machines (25 machines: M1 to M25)
    machines = []
    baseline_stats = {
        "temperature": {"mean": 65.0, "std": 2.5},
        "vibration": {"mean": 1.20, "std": 0.15},
    }

    for i in range(1, 26):
        m_id = f"M{i}"
        plant_id = plants[(i - 1) % len(plants)]["id"]

        if m_id == "M7":
            risk = 0.94
            failure_days = 5
        elif m_id == "M12":
            risk = 0.88
            failure_days = 4
        else:
            noise_temp = 65.0 + rng.uniform(-1.5, 1.5)
            noise_vibe = 1.20 + rng.uniform(-0.1, 0.1)
            recent_readings = [{"temperature": noise_temp, "vibration": noise_vibe}]
            risk, failure_days = compute_machine_risk(recent_readings, baseline_stats)
            risk = round(rng.uniform(0.04, 0.22), 2)
            failure_days = rng.randint(65, 140)

        machines.append({
            "id": m_id,
            "name": f"CNC-Unit-{m_id}",
            "failure_risk": risk,
            "predicted_failure_days": failure_days,
            "plant_id": plant_id,
        })

    # 7. Parts (~60 parts)
    parts = []
    m7_parts = [
        {"id": "PART_M7_ROTOR", "name": "Precision High-RPM Rotor", "cost": 420.0},
        {"id": "PART_M7_STATOR", "name": "Electromagnetic Stator Assembly", "cost": 310.0},
        {"id": "PART_M7_SHAFT", "name": "Hardened Drive Core Shaft", "cost": 185.0},
    ]
    parts.extend(m7_parts)

    m12_parts = [
        {"id": "PART_M12_VALVE", "name": "Cryogenic Metering Valve", "cost": 140.0},
        {"id": "PART_M12_NOZZLE", "name": "Ceramic Spray Nozzle", "cost": 95.0},
    ]
    parts.extend(m12_parts)

    spof_part = {"id": "PART_SPOF_ALLOY", "name": "Monopoly Ultra-Purity Alloy Core", "cost": 850.0}
    parts.append(spof_part)

    for i in range(1, 55):
        p_id = f"PART_{i:02d}"
        parts.append({
            "id": p_id,
            "name": f"Industrial Component {i:02d}",
            "cost": round(rng.uniform(25.0, 350.0), 2),
        })

    # 8. Products (20 products)
    products = []
    for i in range(1, 21):
        p_id = f"P{i}"
        name = f"Industrial System {p_id}"
        if p_id == "P4":
            name = "P4 Smart Turbine Module"
            forecast = 1200
            safety_stock = 200
        elif p_id == "P12":
            name = "P12 Digital Flow Controller"
            forecast = 520
            safety_stock = 120
        else:
            base_sales = rng.randint(300, 900)
            sales_history = [base_sales + rng.randint(-50, 50) for _ in range(6)]
            forecast = compute_demand_forecast(sales_history)
            safety_stock = compute_safety_stock(forecast)

        products.append({
            "id": p_id,
            "name": name,
            "forecast_30d": forecast,
            "safety_stock": safety_stock,
        })

    # 9. Relationships
    machine_produces = []
    for p in m7_parts:
        machine_produces.append({"m_id": "M7", "pt_id": p["id"]})

    for p in m12_parts:
        machine_produces.append({"m_id": "M12", "pt_id": p["id"]})
        machine_produces.append({"m_id": "M13", "pt_id": p["id"]})

    non_planted_machines = [f"M{i}" for i in range(1, 26) if i not in (7, 12)]
    for pt in parts:
        if pt["id"] in [p["id"] for p in m7_parts] or pt["id"] in [p["id"] for p in m12_parts]:
            continue
        if pt["id"] == "PART_SPOF_ALLOY":
            continue
        assigned_machines = rng.sample(non_planted_machines, k=rng.choice([1, 2]))
        for m in assigned_machines:
            machine_produces.append({"m_id": m, "pt_id": pt["id"]})

    supplier_supplies = []
    for p in m7_parts:
        supplier_supplies.append({"s_id": "SUPPLIER_ALT_M7", "pt_id": p["id"], "lead_time": 12})

    supplier_supplies.append({"s_id": "SUPPLIER_SOLO_SPOF", "pt_id": "PART_SPOF_ALLOY", "lead_time": 28})

    regular_suppliers = [s["id"] for s in suppliers if s["id"] not in ("SUPPLIER_ALT_M7", "SUPPLIER_SOLO_SPOF")]
    for pt in parts:
        if pt["id"] in [p["id"] for p in m7_parts] or pt["id"] == "PART_SPOF_ALLOY":
            continue
        num_sups = rng.randint(1, 3)
        assigned_sups = rng.sample(regular_suppliers, k=num_sups)
        for s in assigned_sups:
            lead_time = rng.randint(4, 15)
            supplier_supplies.append({"s_id": s, "pt_id": pt["id"], "lead_time": lead_time})

    part_used_in = []
    for p in m7_parts:
        part_used_in.append({"pt_id": p["id"], "prod_id": "P4", "qty": 1})

    for p in m12_parts:
        part_used_in.append({"pt_id": p["id"], "prod_id": "P12", "qty": 2})

    part_used_in.append({"pt_id": "PART_SPOF_ALLOY", "prod_id": "P1", "qty": 1})
    part_used_in.append({"pt_id": "PART_SPOF_ALLOY", "prod_id": "P5", "qty": 1})

    regular_parts = [pt["id"] for pt in parts if pt["id"] not in [p["id"] for p in m7_parts] and pt["id"] not in [p["id"] for p in m12_parts] and pt["id"] != "PART_SPOF_ALLOY"]
    for prod in products:
        if prod["id"] in ("P4", "P12"):
            extra = rng.sample(regular_parts, k=2)
            for e in extra:
                part_used_in.append({"pt_id": e, "prod_id": prod["id"], "qty": rng.randint(1, 3)})
        else:
            assigned = rng.sample(regular_parts, k=rng.randint(3, 6))
            for a in assigned:
                part_used_in.append({"pt_id": a, "prod_id": prod["id"], "qty": rng.randint(1, 4)})

    product_stocked = []
    for prod in products:
        p_id = prod["id"]
        if p_id == "P4":
            product_stocked.append({"prod_id": p_id, "wh_id": "WH_MIDWEST", "qty": 250})
            product_stocked.append({"prod_id": p_id, "wh_id": "WH_EAST_COAST", "qty": 150})
        elif p_id == "P12":
            product_stocked.append({"prod_id": p_id, "wh_id": "WH_CENTRAL_EU", "qty": 1200})
            product_stocked.append({"prod_id": p_id, "wh_id": "WH_NORDIC", "qty": 1200})
        else:
            wh_sample = rng.sample(warehouses, k=rng.randint(2, 4))
            for wh in wh_sample:
                qty = rng.randint(250, 750)
                product_stocked.append({"prod_id": p_id, "wh_id": wh["id"], "qty": qty})

    warehouse_serves = []
    for cust in customers:
        wh_choices = rng.sample(warehouses, k=rng.choice([1, 2]))
        for wh in wh_choices:
            warehouse_serves.append({"wh_id": wh["id"], "c_id": cust["id"]})

    return {
        "regions": regions,
        "plants": plants,
        "warehouses": warehouses,
        "customers": customers,
        "suppliers": suppliers,
        "alternate_suppliers": alternate_suppliers,
        "machines": machines,
        "parts": parts,
        "products": products,
        "machine_produces": machine_produces,
        "supplier_supplies": supplier_supplies,
        "part_used_in": part_used_in,
        "product_stocked": product_stocked,
        "warehouse_serves": warehouse_serves,
    }


def seed_database() -> Dict[str, int]:
    """Execute batched, idempotent Cypher transactions to populate FalkorDB graph."""
    cfg = get_connection_config()
    graph = get_graph()

    # Idempotent reset: delete all nodes and relationships cleanly
    try:
        graph.query("MATCH (n) DETACH DELETE n")
    except Exception:
        pass

    data = build_synthetic_dataset()

    # 1. Batch create Regions
    graph.query(
        "UNWIND $batch AS r CREATE (:Region {id: r.id, name: r.name})",
        params={"batch": data["regions"]}
    )

    # 2. Batch create Plants
    graph.query(
        "UNWIND $batch AS p CREATE (:Plant {id: p.id, name: p.name, location: p.location})",
        params={"batch": data["plants"]}
    )

    # 3. Batch create Warehouses
    graph.query(
        "UNWIND $batch AS w CREATE (:Warehouse {id: w.id, name: w.name, location: w.location, capacity: w.capacity})",
        params={"batch": data["warehouses"]}
    )

    # 4. Batch create Customers
    graph.query(
        "UNWIND $batch AS c CREATE (:Customer {id: c.id, name: c.name, tier: c.tier})",
        params={"batch": data["customers"]}
    )

    # 5. Batch create Suppliers & link to Regions
    graph.query(
        """
        UNWIND $batch AS s
        MATCH (r:Region {id: s.region})
        CREATE (sup:Supplier {id: s.id, name: s.name, rating: s.rating})-[:LOCATED_IN]->(r)
        """,
        params={"batch": data["suppliers"]}
    )

    # 6. Batch Supplier ALTERNATE_FOR relationships
    graph.query(
        """
        UNWIND $batch AS pair
        MATCH (s1:Supplier {id: pair.s1}), (s2:Supplier {id: pair.s2})
        CREATE (s1)-[:ALTERNATE_FOR]->(s2)
        CREATE (s2)-[:ALTERNATE_FOR]->(s1)
        """,
        params={"batch": data["alternate_suppliers"]}
    )

    # 7. Batch create Machines & link Plant -> HAS -> Machine
    graph.query(
        """
        UNWIND $batch AS m
        MATCH (pl:Plant {id: m.plant_id})
        CREATE (pl)-[:HAS]->(mach:Machine {
            id: m.id,
            name: m.name,
            failure_risk: m.failure_risk,
            predicted_failure_days: m.predicted_failure_days
        })
        """,
        params={"batch": data["machines"]}
    )

    # 8. Batch create Parts
    graph.query(
        "UNWIND $batch AS pt CREATE (:Part {id: pt.id, name: pt.name, cost: pt.cost})",
        params={"batch": data["parts"]}
    )

    # 9. Batch create Products
    graph.query(
        """
        UNWIND $batch AS prod
        CREATE (:Product {
            id: prod.id,
            name: prod.name,
            forecast_30d: prod.forecast_30d,
            safety_stock: prod.safety_stock
        })
        """,
        params={"batch": data["products"]}
    )

    # 10. Batch Machine -[:PRODUCES]-> Part
    graph.query(
        """
        UNWIND $batch AS rel
        MATCH (m:Machine {id: rel.m_id}), (pt:Part {id: rel.pt_id})
        CREATE (m)-[:PRODUCES]->(pt)
        """,
        params={"batch": data["machine_produces"]}
    )

    # 11. Batch Supplier -[:SUPPLIES {lead_time_days}]-> Part
    graph.query(
        """
        UNWIND $batch AS rel
        MATCH (s:Supplier {id: rel.s_id}), (pt:Part {id: rel.pt_id})
        CREATE (s)-[:SUPPLIES {lead_time_days: rel.lead_time}]->(pt)
        """,
        params={"batch": data["supplier_supplies"]}
    )

    # 12. Batch Part -[:USED_IN {qty_per_unit}]-> Product
    graph.query(
        """
        UNWIND $batch AS rel
        MATCH (pt:Part {id: rel.pt_id}), (prod:Product {id: rel.prod_id})
        CREATE (pt)-[:USED_IN {qty_per_unit: rel.qty}]->(prod)
        """,
        params={"batch": data["part_used_in"]}
    )

    # 13. Batch Product -[:STOCKED_AT {qty}]-> Warehouse
    graph.query(
        """
        UNWIND $batch AS rel
        MATCH (prod:Product {id: rel.prod_id}), (wh:Warehouse {id: rel.wh_id})
        CREATE (prod)-[:STOCKED_AT {qty: rel.qty}]->(wh)
        """,
        params={"batch": data["product_stocked"]}
    )

    # 14. Batch Warehouse -[:SERVES]-> Customer
    graph.query(
        """
        UNWIND $batch AS rel
        MATCH (wh:Warehouse {id: rel.wh_id}), (c:Customer {id: rel.c_id})
        CREATE (wh)-[:SERVES]->(c)
        """,
        params={"batch": data["warehouse_serves"]}
    )

    # 15. Seed Predictive Maintenance & Demand Forecasting Graph
    try:
        from scripts.seed_pdm_and_forecasting import seed_pdm_and_forecasting
        seed_pdm_and_forecasting()
    except Exception as e:
        print(f"Warning: Failed to seed PdM and forecasting nodes: {e}")

    # Verification counts
    counts = {}
    node_labels = ["Plant", "Machine", "Part", "Product", "Supplier", "Warehouse", "Customer", "Region", "SensorTelemetry", "PdMPrescription", "DemandForecast"]
    for label in node_labels:
        res = graph.query(f"MATCH (n:{label}) RETURN count(n)").result_set
        counts[f"Nodes:{label}"] = res[0][0]

    rel_types = ["HAS", "PRODUCES", "SUPPLIES", "USED_IN", "STOCKED_AT", "SERVES", "LOCATED_IN", "ALTERNATE_FOR", "HAS_TELEMETRY", "HAS_PDM_PLAN", "HAS_FORECAST", "COMMITTED_DEMAND"]
    for rel in rel_types:
        res = graph.query(f"MATCH ()-[r:{rel}]->() RETURN count(r)").result_set
        counts[f"Rels:{rel}"] = res[0][0]

    return counts


if __name__ == "__main__":
    cfg = get_connection_config()
    print(f"Seeding FalkorDB graph '{cfg['graph_name']}' on {cfg['host']}:{cfg['port']}...")
    summary = seed_database()
    print("Seed Complete! Verification Counts:")
    for k, v in summary.items():
        print(f"  {k:20s}: {v}")
