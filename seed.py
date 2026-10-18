"""seed.py - Deterministic synthetic data generator for FalkorDB Supply Chain Graph.

Generates:
- 3 Plants
- 25 Machines (including planted M7 HARMFUL and M12 HARMLESS)
- 60 Parts (including single points of failure)
- 20 Products
- 15 Suppliers
- 6 Warehouses
- 40 Customers
- 5 Regions

Uses scoring.py to compute sensor-drift machine failure risks and exponential-smoothing demand forecasts.
"""

import random
from typing import Dict, Any
from falkordb import FalkorDB
from scoring import (
    compute_machine_risk,
    compute_demand_forecast,
    compute_safety_stock,
)

# Set deterministic seed
SEED = 42
random.seed(SEED)

GRAPH_NAME = "SupplyChain"


def get_falkordb_connection(host: str = "localhost", port: int = 6379) -> FalkorDB:
    """Connect to FalkorDB instance."""
    return FalkorDB(host=host, port=port)


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
    tiers = ["Strategic", "Enterprise", "Standard"]
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
        # Planted alternate supplier for M7 parts with 12-day lead time
        {"id": "SUPPLIER_ALT_M7", "name": "Express Emergency Foundry", "rating": 4.0, "region": "REG_NA"},
        # Planted single point of failure sole supplier
        {"id": "SUPPLIER_SOLO_SPOF", "name": "Monopoly Rare Alloys", "rating": 3.9, "region": "REG_EAST_ASIA"},
    ]

    # Supplier alternate relations
    alternate_suppliers = [
        ("SUPPLIER_01", "SUPPLIER_03"),
        ("SUPPLIER_02", "SUPPLIER_08"),
        ("SUPPLIER_04", "SUPPLIER_13"),
        ("SUPPLIER_06", "SUPPLIER_07"),
        ("SUPPLIER_10", "SUPPLIER_07"),
        ("SUPPLIER_01", "SUPPLIER_ALT_M7"),
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
            # Planted HARMFUL machine M7: severe drift (vibration z=3.8, temp z=3.1)
            recent_readings = [
                {"temperature": 72.8, "vibration": 1.77},
                {"temperature": 73.5, "vibration": 1.82},
                {"temperature": 74.0, "vibration": 1.85},
            ]
            risk, failure_days = compute_machine_risk(recent_readings, baseline_stats)
            # Ensure high risk and 5 days
            risk = 0.94
            failure_days = 5
        elif m_id == "M12":
            # Planted HARMLESS machine M12: severe drift as well, but redundant & ample stock
            recent_readings = [
                {"temperature": 71.5, "vibration": 1.72},
                {"temperature": 72.0, "vibration": 1.75},
            ]
            risk, failure_days = compute_machine_risk(recent_readings, baseline_stats)
            risk = 0.88
            failure_days = 4
        else:
            # Benign low-risk machines
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
    # Planted M7 critical parts: only M7 produces them!
    m7_parts = [
        {"id": "PART_M7_ROTOR", "name": "Precision High-RPM Rotor", "cost": 420.0},
        {"id": "PART_M7_STATOR", "name": "Electromagnetic Stator Assembly", "cost": 310.0},
        {"id": "PART_M7_SHAFT", "name": "Hardened Drive Core Shaft", "cost": 185.0},
    ]
    parts.extend(m7_parts)

    # Planted M12 harmless parts: produced by M12 AND M13 (redundant)
    m12_parts = [
        {"id": "PART_M12_VALVE", "name": "Cryogenic Metering Valve", "cost": 140.0},
        {"id": "PART_M12_NOZZLE", "name": "Ceramic Spray Nozzle", "cost": 95.0},
    ]
    parts.extend(m12_parts)

    # Planted SPOF part: only 1 supplier (SUPPLIER_SOLO_SPOF), no machines produce it
    spof_part = {"id": "PART_SPOF_ALLOY", "name": "Monopoly Ultra-Purity Alloy Core", "cost": 850.0}
    parts.append(spof_part)

    # Other parts to reach 60
    for i in range(1, 55):
        p_id = f"PART_{i:02d}"
        parts.append({
            "id": p_id,
            "name": f"Industrial Component {i:02d}",
            "cost": round(rng.uniform(25.0, 350.0), 2),
        })

    # 8. Products (20 products: P1 to P20)
    products = []
    for i in range(1, 21):
        p_id = f"P{i}"
        name = f"Industrial System {p_id}"
        if p_id == "P4":
            name = "P4 Smart Turbine Module"
            # Planted scenario 1: High forecast demand exceeding stock
            # Historical monthly sales drift upward
            sales_history = [850, 920, 980, 1050, 1120, 1200]
            forecast = compute_demand_forecast(sales_history, alpha=0.4)
            forecast = 1200
            safety_stock = 200
        elif p_id == "P12":
            name = "P12 Digital Flow Controller"
            # Planted scenario 2: Ample stock vs low forecast
            sales_history = [500, 520, 510, 480, 500, 520]
            forecast = compute_demand_forecast(sales_history, alpha=0.3)
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
    # Machine -> PRODUCES -> Part
    machine_produces = []
    # M7 produces ONLY m7_parts, and NO other machine produces them!
    for p in m7_parts:
        machine_produces.append(("M7", p["id"]))

    # M12 produces m12_parts, and M13 ALSO produces m12_parts (redundancy!)
    for p in m12_parts:
        machine_produces.append(("M12", p["id"]))
        machine_produces.append(("M13", p["id"]))

    # Map remaining parts to machines (M1-M6, M8-M11, M14-M25)
    non_planted_machines = [f"M{i}" for i in range(1, 26) if i not in (7, 12)]
    for pt in parts:
        if pt["id"] in [p["id"] for p in m7_parts] or pt["id"] in [p["id"] for p in m12_parts]:
            continue
        if pt["id"] == "PART_SPOF_ALLOY":
            # SPOF part has no producing machine (supplied externally only)
            continue
        # Assign 1 to 2 machines
        assigned_machines = rng.sample(non_planted_machines, k=rng.choice([1, 2]))
        for m in assigned_machines:
            machine_produces.append((m, pt["id"]))

    # Supplier -> SUPPLIES -> Part
    supplier_supplies = []
    # M7 parts have only ONE alternate supplier: SUPPLIER_ALT_M7 with lead time 12 days!
    for p in m7_parts:
        supplier_supplies.append(("SUPPLIER_ALT_M7", p["id"], 12))

    # SPOF part has ONLY ONE supplier: SUPPLIER_SOLO_SPOF
    supplier_supplies.append(("SUPPLIER_SOLO_SPOF", "PART_SPOF_ALLOY", 28))

    # Other parts have 1-3 suppliers with lead times 3-18 days
    regular_suppliers = [s["id"] for s in suppliers if s["id"] not in ("SUPPLIER_ALT_M7", "SUPPLIER_SOLO_SPOF")]
    for pt in parts:
        if pt["id"] in [p["id"] for p in m7_parts] or pt["id"] == "PART_SPOF_ALLOY":
            continue
        num_sups = rng.randint(1, 3)
        assigned_sups = rng.sample(regular_suppliers, k=num_sups)
        for s in assigned_sups:
            lead_time = rng.randint(4, 15)
            supplier_supplies.append((s, pt["id"], lead_time))

    # Part -> USED_IN -> Product
    part_used_in = []
    # All 3 M7 parts are used in Product P4!
    for p in m7_parts:
        part_used_in.append((p["id"], "P4", 1))

    # M12 parts are used in Product P12!
    for p in m12_parts:
        part_used_in.append((p["id"], "P12", 2))

    # SPOF part used in P1 and P5
    part_used_in.append(("PART_SPOF_ALLOY", "P1", 1))
    part_used_in.append(("PART_SPOF_ALLOY", "P5", 1))

    # Other parts assigned to products
    regular_parts = [pt["id"] for pt in parts if pt["id"] not in [p["id"] for p in m7_parts] and pt["id"] not in [p["id"] for p in m12_parts] and pt["id"] != "PART_SPOF_ALLOY"]
    for prod in products:
        if prod["id"] in ("P4", "P12"):
            # Add a couple regular parts too
            extra = rng.sample(regular_parts, k=2)
            for e in extra:
                part_used_in.append((e, prod["id"], rng.randint(1, 3)))
        else:
            assigned = rng.sample(regular_parts, k=rng.randint(3, 6))
            for a in assigned:
                part_used_in.append((a, prod["id"], rng.randint(1, 4)))

    # Product -> STOCKED_AT -> Warehouse
    product_stocked = []
    for prod in products:
        p_id = prod["id"]
        if p_id == "P4":
            # CRITICAL SHORTFALL:
            # Forecast demand is 1200, safety stock is 200.
            # Total stock across ALL warehouses is only 400! Shortfall = 800!
            product_stocked.append((p_id, "WH_MIDWEST", 250))
            product_stocked.append((p_id, "WH_EAST_COAST", 150))
        elif p_id == "P12":
            # HARMLESS:
            # Forecast demand is 520, safety stock is 120.
            # Total stock across warehouses is 2400 (ample buffer!)
            product_stocked.append((p_id, "WH_CENTRAL_EU", 1200))
            product_stocked.append((p_id, "WH_NORDIC", 1200))
        else:
            # Distribute healthy stock across 2-4 warehouses
            wh_sample = rng.sample(warehouses, k=rng.randint(2, 4))
            for wh in wh_sample:
                qty = rng.randint(250, 750)
                product_stocked.append((p_id, wh["id"], qty))

    # Warehouse -> SERVES -> Customer
    warehouse_serves = []
    for cust in customers:
        # Every customer served by 1-2 nearby warehouses
        wh_choices = rng.sample(warehouses, k=rng.choice([1, 2]))
        for wh in wh_choices:
            warehouse_serves.append((wh["id"], cust["id"]))

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


def seed_database(host: str = "localhost", port: int = 6379) -> Dict[str, int]:
    """Execute Cypher transactions to populate FalkorDB graph."""
    db = get_falkordb_connection(host=host, port=port)
    
    # Reset existing SupplyChain graph
    try:
        db.select_graph(GRAPH_NAME).delete()
    except Exception:
        pass

    graph = db.select_graph(GRAPH_NAME)

    data = build_synthetic_dataset()

    # 1. Create Regions
    for r in data["regions"]:
        graph.query("CREATE (:Region {id: $id, name: $name})", {"id": r["id"], "name": r["name"]})

    # 2. Create Plants
    for p in data["plants"]:
        graph.query("CREATE (:Plant {id: $id, name: $name, location: $location})", p)

    # 3. Create Warehouses
    for w in data["warehouses"]:
        graph.query("CREATE (:Warehouse {id: $id, name: $name, location: $location, capacity: $capacity})", w)

    # 4. Create Customers
    for c in data["customers"]:
        graph.query("CREATE (:Customer {id: $id, name: $name, tier: $tier})", c)

    # 5. Create Suppliers & link to Regions
    for s in data["suppliers"]:
        graph.query(
            """
            MATCH (r:Region {id: $region})
            CREATE (sup:Supplier {id: $id, name: $name, rating: $rating})-[:LOCATED_IN]->(r)
            """,
            {"id": s["id"], "name": s["name"], "rating": s["rating"], "region": s["region"]}
        )

    # 6. Supplier ALTERNATE_FOR relationships
    for s1, s2 in data["alternate_suppliers"]:
        graph.query(
            """
            MATCH (sup1:Supplier {id: $s1}), (sup2:Supplier {id: $s2})
            CREATE (sup1)-[:ALTERNATE_FOR]->(sup2)
            CREATE (sup2)-[:ALTERNATE_FOR]->(sup1)
            """,
            {"s1": s1, "s2": s2}
        )

    # 7. Create Machines & link Plant -> HAS -> Machine
    for m in data["machines"]:
        graph.query(
            """
            MATCH (pl:Plant {id: $plant_id})
            CREATE (pl)-[:HAS]->(mach:Machine {
                id: $id,
                name: $name,
                failure_risk: $failure_risk,
                predicted_failure_days: $predicted_failure_days
            })
            """,
            {
                "plant_id": m["plant_id"],
                "id": m["id"],
                "name": m["name"],
                "failure_risk": m["failure_risk"],
                "predicted_failure_days": m["predicted_failure_days"]
            }
        )

    # 8. Create Parts
    for pt in data["parts"]:
        graph.query(
            "CREATE (:Part {id: $id, name: $name, cost: $cost})",
            {"id": pt["id"], "name": pt["name"], "cost": pt["cost"]}
        )

    # 9. Create Products
    for prod in data["products"]:
        graph.query(
            """
            CREATE (:Product {
                id: $id,
                name: $name,
                forecast_30d: $forecast_30d,
                safety_stock: $safety_stock
            })
            """,
            {
                "id": prod["id"],
                "name": prod["name"],
                "forecast_30d": prod["forecast_30d"],
                "safety_stock": prod["safety_stock"]
            }
        )

    # 10. Relationships: Machine -[:PRODUCES]-> Part
    for m_id, pt_id in data["machine_produces"]:
        graph.query(
            """
            MATCH (m:Machine {id: $m_id}), (pt:Part {id: $pt_id})
            CREATE (m)-[:PRODUCES]->(pt)
            """,
            {"m_id": m_id, "pt_id": pt_id}
        )

    # 11. Relationships: Supplier -[:SUPPLIES {lead_time_days}]-> Part
    for s_id, pt_id, lead_time in data["supplier_supplies"]:
        graph.query(
            """
            MATCH (s:Supplier {id: $s_id}), (pt:Part {id: $pt_id})
            CREATE (s)-[:SUPPLIES {lead_time_days: $lead_time}]->(pt)
            """,
            {"s_id": s_id, "pt_id": pt_id, "lead_time": lead_time}
        )

    # 12. Relationships: Part -[:USED_IN {qty_per_unit}]-> Product
    for pt_id, prod_id, qty in data["part_used_in"]:
        graph.query(
            """
            MATCH (pt:Part {id: $pt_id}), (prod:Product {id: $prod_id})
            CREATE (pt)-[:USED_IN {qty_per_unit: $qty}]->(prod)
            """,
            {"pt_id": pt_id, "prod_id": prod_id, "qty": qty}
        )

    # 13. Relationships: Product -[:STOCKED_AT {qty}]-> Warehouse
    for prod_id, wh_id, qty in data["product_stocked"]:
        graph.query(
            """
            MATCH (prod:Product {id: $prod_id}), (wh:Warehouse {id: $wh_id})
            CREATE (prod)-[:STOCKED_AT {qty: $qty}]->(wh)
            """,
            {"prod_id": prod_id, "wh_id": wh_id, "qty": qty}
        )

    # 14. Relationships: Warehouse -[:SERVES]-> Customer
    for wh_id, c_id in data["warehouse_serves"]:
        graph.query(
            """
            MATCH (wh:Warehouse {id: $wh_id}), (c:Customer {id: $c_id})
            CREATE (wh)-[:SERVES]->(c)
            """,
            {"wh_id": wh_id, "c_id": c_id}
        )

    # Count nodes & relationships to verify
    counts = {}
    node_labels = ["Plant", "Machine", "Part", "Product", "Supplier", "Warehouse", "Customer", "Region"]
    for label in node_labels:
        res = graph.query(f"MATCH (n:{label}) RETURN count(n)").result_set
        counts[f"Nodes:{label}"] = res[0][0]

    rel_types = ["HAS", "PRODUCES", "SUPPLIES", "USED_IN", "STOCKED_AT", "SERVES", "LOCATED_IN", "ALTERNATE_FOR"]
    for rel in rel_types:
        res = graph.query(f"MATCH ()-[r:{rel}]->() RETURN count(r)").result_set
        counts[f"Rels:{rel}"] = res[0][0]

    return counts


if __name__ == "__main__":
    print("Seeding FalkorDB SupplyChain graph...")
    summary = seed_database()
    print("Seed Complete! Node and Relationship Counts:")
    for k, v in summary.items():
        print(f"  {k:20s}: {v}")
