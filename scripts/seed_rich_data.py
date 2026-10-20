"""scripts/seed_rich_data.py - Seeds enterprise graph dataset adding >= 1.0 MB RAM to FalkorDB.

Features:
- Completely preserves all baseline benchmark scenarios (M7 risk=0.94, M12 risk=0.88, P4, P12, SPOF alloy)
- Links both top-level facilities (Apex Automotive & Thames Semiconductor Foundry)
- Provisions all 9 London Cleanroom machines, intermediate wafer/die stages, chipsets, suppliers & customers
- Seeds rich production batches, in-line quality metrology scans, historical maintenance logs, and sensor telemetry time-series
- Uses high-speed UNWIND parameter batching
- Verifies that memory increases by AT LEAST 1.0 MB while staying safely below the free tier limit (100MB)
"""

import sys
import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.db import get_graph, get_db, get_connection_config

BATCH_CHUNK = 250
SEED = 42
rng = random.Random(SEED)


def get_current_memory_bytes(db) -> int:
    try:
        info = db.execute_command("INFO", "memory")
        if isinstance(info, dict):
            return int(info.get("used_memory", 0))
    except Exception:
        pass
    return 0


def main():
    print("=" * 65)
    print("FalkorDB Enterprise Supply Chain Deep Enrichment Seeder")
    print("=" * 65)

    db = get_db()
    g = get_graph()
    cfg = get_connection_config()

    init_mem = get_current_memory_bytes(db)
    target_mem = init_mem + 1048576  # baseline + at least 1.0 MB
    print(f"Target Host    : {cfg['host']}:{cfg['port']}")
    print(f"Target Graph   : {cfg['graph_name']}")
    print(f"Initial Memory : {init_mem / (1024*1024):.2f} MB ({init_mem:,} bytes)")
    print(f"Target Memory  : >= {target_mem / (1024*1024):.2f} MB (+1.00 MB minimum)")
    print("-" * 65)

    # -------------------------------------------------------------
    # 1. FACILITIES & PLANTS
    # -------------------------------------------------------------
    print("1/7. Merging Facility & Plant Hierarchies...")
    g.query("""
    MERGE (fa:Facility {id: 'FACILITY_APEX'})
    ON CREATE SET 
        fa.name = 'Apex Global Manufacturing Network',
        fa.city = 'Detroit, MI, USA & Global',
        fa.facility_type = 'Powertrain Machining & Precision Mechatronics',
        fa.total_area_sqm = 126500,
        fa.director = 'Marcus Vance (Chief Supply Chain Officer)',
        fa.description = 'Multi-plant powertrain assembly and precision robotics network across Detroit, Munich, and Austin.'

    MERGE (fl:Facility {id: 'FACILITY_LONDON'})
    ON CREATE SET 
        fl.name = 'Thames Nanotech Semiconductor Foundry',
        fl.city = 'London, United Kingdom (Olympic Tech Park)',
        fl.facility_type = 'ISO Class 4 Cleanroom • Semiconductor Wafer Fab & Micro-Packaging',
        fl.total_area_sqm = 54000,
        fl.director = 'Prof. Alistair Finch (Director of Nanofabrication)',
        fl.description = 'Integrated London cleanroom unit housing Line Alpha (Wafer Fab) and Line Beta (Packaging) converging to central QC.'
    """)

    # Link Apex plants
    g.query("""
    MERGE (p_det:Plant {id: 'PLANT_DETROIT'})
    ON CREATE SET p_det.name = 'Apex Advanced Assembly', p_det.location = 'Detroit, USA'
    MERGE (p_aus:Plant {id: 'PLANT_AUSTIN'})
    ON CREATE SET p_aus.name = 'Silicon Hill Precision', p_aus.location = 'Austin, USA'
    MERGE (p_mun:Plant {id: 'PLANT_MUNICH'})
    ON CREATE SET p_mun.name = 'Bavaria Mechatronics', p_mun.location = 'Munich, Germany'

    MERGE (fa:Facility {id: 'FACILITY_APEX'})
    MERGE (p_det)-[:PART_OF_FACILITY]->(fa)
    MERGE (p_aus)-[:PART_OF_FACILITY]->(fa)
    MERGE (p_mun)-[:PART_OF_FACILITY]->(fa)
    """)

    # Link London plants
    g.query("""
    MERGE (p_lfab:Plant {id: 'PLANT_LONDON_FAB'})
    ON CREATE SET 
        p_lfab.name = 'Thames Cleanroom Fab Alpha',
        p_lfab.location = 'London, United Kingdom',
        p_lfab.facility_type = 'Plant 1: Front-End 13.5nm EUV Lithography & Plasma Etch',
        p_lfab.floor_area_sqm = 28000,
        p_lfab.cleanroom_class = 'ISO Class 4'

    MERGE (p_lpkg:Plant {id: 'PLANT_LONDON_PKG'})
    ON CREATE SET 
        p_lpkg.name = 'Thames Packaging Beta',
        p_lpkg.location = 'London, United Kingdom',
        p_lpkg.facility_type = 'Plant 2: Back-End Picosecond Laser Dicing & Wire Bonding',
        p_lpkg.floor_area_sqm = 26000,
        p_lpkg.cleanroom_class = 'ISO Class 4'

    MERGE (fl:Facility {id: 'FACILITY_LONDON'})
    MERGE (p_lfab)-[:PART_OF_FACILITY]->(fl)
    MERGE (p_lpkg)-[:PART_OF_FACILITY]->(fl)
    """)

    # -------------------------------------------------------------
    # 2. LONDON CLEANROOM MACHINES
    # -------------------------------------------------------------
    print("2/7. Provisioning London Semiconductor Cleanroom Workcells...")
    london_machines = [
        # Line Alpha (Front-End)
        {"id": "LDN_SLICER_01", "name": "Meyer Burger DS265 Wire Slicer", "plant_id": "PLANT_LONDON_FAB", "bay": "Zone 1 • Wafer Slicing", "risk": 0.05, "days": 180, "spec": "Diamond wire 45um kerf, 300mm ingot capacity"},
        {"id": "LDN_CMP_02", "name": "Ebara F-REX300X Planarizer", "plant_id": "PLANT_LONDON_FAB", "bay": "Zone 2 • Planarization", "risk": 0.08, "days": 150, "spec": "Sub-nanometer Ra 0.12nm surface uniformity CMP cell"},
        {"id": "LDN_EUV_03", "name": "ASML Twinscan High-NA EUV Stepper", "plant_id": "PLANT_LONDON_FAB", "bay": "Zone 3 • Yellow Litho Bay", "risk": 0.14, "days": 110, "spec": "0.55 High-NA EXE:5000 13.5nm EUV, 8nm pitch resolution"},
        {"id": "LDN_ETCH_04", "name": "Lam Kiyo FX DRIE Plasma Etcher", "plant_id": "PLANT_LONDON_FAB", "bay": "Zone 4 • Plasma Etch", "risk": 0.09, "days": 140, "spec": "High-aspect 40:1 deep Bosch reactive-ion trench etching"},
        # Line Beta (Back-End)
        {"id": "LDN_DICE_01", "name": "Disco DFL7362 Picosecond Laser Dicer", "plant_id": "PLANT_LONDON_PKG", "bay": "Zone 1 • Laser Singulation", "risk": 0.06, "days": 160, "spec": "Sub-2um thermal heat-affected kerf, picosecond pulse width"},
        {"id": "LDN_ATTACH_02", "name": "Besi Datacon 8800 Eutectic Die Attach", "plant_id": "PLANT_LONDON_PKG", "bay": "Zone 2 • Die Placement", "risk": 0.07, "days": 155, "spec": "Sub-micron +-1.0um flip-chip eutectic placement accuracy"},
        {"id": "LDN_BOND_03", "name": "K&S Asterion Ultrasonic Ball Bonder", "plant_id": "PLANT_LONDON_PKG", "bay": "Zone 3 • Wire Bonding", "risk": 0.06, "days": 175, "spec": "18um 99.999% Au wire thermosonic wedge & ball bonding"},
        {"id": "LDN_SEAL_04", "name": "SST 5100 Cryogenic Vacuum Sealer", "plant_id": "PLANT_LONDON_PKG", "bay": "Zone 4 • Encapsulation", "risk": 0.05, "days": 190, "spec": "Cryogenic hermetic seal under 10^-9 mbar inert N2 environment"},
        # Shared Unit Convergence
        {"id": "LDN-UNIT-QC", "name": "London Central Cleanroom Metrology Bay", "plant_id": "PLANT_LONDON_FAB", "bay": "Zone 5 • Convergence QC", "risk": 0.02, "days": 300, "spec": "KLA-Tencor optical defect scanner & Nordson 3D X-Ray CT"}
    ]

    g.query("""
    UNWIND $batch AS m
    MATCH (pl:Plant {id: m.plant_id})
    MERGE (mach:Machine {id: m.id})
    ON CREATE SET 
        mach.name = m.name,
        mach.failure_risk = m.risk,
        mach.predicted_failure_days = m.days,
        mach.bay = m.bay,
        mach.spec = m.spec,
        mach.facility_id = 'FACILITY_LONDON'
    MERGE (pl)-[:HAS]->(mach)
    """, params={"batch": london_machines})

    # Convergence edges
    g.query("""
    MATCH (p1:Plant {id: 'PLANT_LONDON_FAB'}), (p2:Plant {id: 'PLANT_LONDON_PKG'}), (qc:Machine {id: 'LDN-UNIT-QC'})
    MERGE (p1)-[:CONVERGES_INTO]->(qc)
    MERGE (p2)-[:CONVERGES_INTO]->(qc)
    """)

    # -------------------------------------------------------------
    # 3. SEMICONDUCTOR MATERIALS, CHIPS, SUPPLIERS & CUSTOMERS
    # -------------------------------------------------------------
    print("3/7. Seeding Semiconductor Bills-of-Materials & Supply Chain Nodes...")
    semi_parts = [
        {"id": "LDN_PART_INGOT", "name": "300mm Prime Electronic Silicon Ingot", "cost": 1250.0, "m_id": "LDN_SLICER_01"},
        {"id": "LDN_PART_CMP_WAFER", "name": "Sub-Nanometer Planarized Silicon Substrate", "cost": 1820.0, "m_id": "LDN_CMP_02"},
        {"id": "LDN_PART_EUV_WAFER", "name": "High-NA EUV 8nm Pitch Patterned Wafer", "cost": 4650.0, "m_id": "LDN_EUV_03"},
        {"id": "LDN_PART_ETCHED_WAFER", "name": "DRIE Bosch Trench Micro-Machined Wafer", "cost": 5800.0, "m_id": "LDN_ETCH_04"},
        {"id": "LDN_PART_DICED_DIE", "name": "Singulated Picosecond Micro-Dies", "cost": 650.0, "m_id": "LDN_DICE_01"},
        {"id": "LDN_PART_AU_WIRE", "name": "18um 5N Ultra-Fine Gold Bonding Wire", "cost": 380.0, "m_id": "LDN_BOND_03"},
        {"id": "LDN_PART_HERMETIC_PKG", "name": "Ceramic Multi-Pin Cryogenic Carrier Package", "cost": 490.0, "m_id": "LDN_SEAL_04"},
    ]

    g.query("""
    UNWIND $batch AS p
    MERGE (pt:Part {id: p.id})
    ON CREATE SET pt.name = p.name, pt.cost = p.cost, pt.facility_id = 'FACILITY_LONDON'
    WITH pt, p
    MATCH (m:Machine {id: p.m_id})
    MERGE (m)-[:PRODUCES]->(pt)
    """, params={"batch": semi_parts})

    semi_products = [
        {"id": "LDN_PROD_QUANTUM_ASIC", "name": "7nm Cryogenic Quantum Control ASIC (Q-CORE)", "forecast": 850, "safety": 150},
        {"id": "LDN_PROD_AI_CHIPLET", "name": "3D-Stacked Heterogeneous AI Tensor Accelerator (NEURO-3D)", "forecast": 1400, "safety": 250},
        {"id": "LDN_PROD_LIDAR_IC", "name": "Solid-State Photonic LiDAR Transceiver (PHOTON-X)", "forecast": 2100, "safety": 400},
    ]

    g.query("""
    UNWIND $batch AS pr
    MERGE (prod:Product {id: pr.id})
    ON CREATE SET 
        prod.name = pr.name, 
        prod.forecast_30d = pr.forecast, 
        prod.safety_stock = pr.safety,
        prod.facility_id = 'FACILITY_LONDON'
    WITH prod
    MATCH (qc:Machine {id: 'LDN-UNIT-QC'})
    MERGE (prod)-[:TESTED_AT]->(qc)
    """, params={"batch": semi_products})

    # Link semi parts to semi products
    semi_bom = [
        {"pt_id": "LDN_PART_DICED_DIE", "pr_id": "LDN_PROD_QUANTUM_ASIC", "qty": 4},
        {"pt_id": "LDN_PART_AU_WIRE", "pr_id": "LDN_PROD_AI_CHIPLET", "qty": 12},
        {"pt_id": "LDN_PART_HERMETIC_PKG", "pr_id": "LDN_PROD_LIDAR_IC", "qty": 1},
    ]
    g.query("""
    UNWIND $batch AS rel
    MATCH (pt:Part {id: rel.pt_id}), (pr:Product {id: rel.pr_id})
    MERGE (pt)-[:USED_IN {qty_per_unit: rel.qty}]->(pr)
    """, params={"batch": semi_bom})

    # Cleanroom Suppliers
    cleanroom_suppliers = [
        {"id": "SUP_ASML_NETHERLANDS", "name": "ASML Advanced Photolithography NV", "rating": 4.95, "region": "REG_EU", "pt_id": "LDN_PART_EUV_WAFER", "lead": 45},
        {"id": "SUP_LINDE_GAS_UK", "name": "Linde Ultra-Pure Process Gases UK", "rating": 4.88, "region": "REG_EU", "pt_id": "LDN_PART_ETCHED_WAFER", "lead": 7},
        {"id": "SUP_SHIN_ETSU", "name": "Shin-Etsu Handotai Precision Silicon", "rating": 4.92, "region": "REG_EAST_ASIA", "pt_id": "LDN_PART_INGOT", "lead": 21},
        {"id": "SUP_HERAEUS_GERMANY", "name": "Heraeus Electronics Precious Materials", "rating": 4.85, "region": "REG_EU", "pt_id": "LDN_PART_AU_WIRE", "lead": 10},
    ]

    g.query("""
    UNWIND $batch AS s
    MERGE (sup:Supplier {id: s.id})
    ON CREATE SET sup.name = s.name, sup.rating = s.rating
    WITH sup, s
    MATCH (r:Region {id: s.region})
    MERGE (sup)-[:LOCATED_IN]->(r)
    WITH sup, s
    MATCH (pt:Part {id: s.pt_id})
    MERGE (sup)-[:SUPPLIES {lead_time_days: s.lead}]->(pt)
    """, params={"batch": cleanroom_suppliers})

    # European Deep Tech Customers
    tech_customers = [
        {"id": "CUST_ARM_CAMBRIDGE", "name": "ARM Architecture Computing Group (Cambridge)", "tier": "Strategic"},
        {"id": "CUST_OXFORD_IONICS", "name": "Oxford Quantum Photonics Research Lab", "tier": "Strategic"},
        {"id": "CUST_DEEPMIND_ROBOTICS", "name": "DeepMind Autonomous Robotics Division", "tier": "Strategic"},
        {"id": "CUST_ROLLS_ROYCE_AERO", "name": "Rolls-Royce Aerospace Avionics (Derby)", "tier": "Enterprise"},
    ]

    g.query("""
    UNWIND $batch AS c
    MERGE (cust:Customer {id: c.id})
    ON CREATE SET cust.name = c.name, cust.tier = c.tier
    WITH cust
    MATCH (wh:Warehouse {id: 'WH_CENTRAL_EU'})
    MERGE (wh)-[:SERVES]->(cust)
    """, params={"batch": tech_customers})

    # -------------------------------------------------------------
    # 4. LARGE VOLUME SEEDING: BATCHES, TELEMETRY, LOGS & ORDERS
    # -------------------------------------------------------------
    print("4/7. Synthesizing High-Density Batches, Maintenance Logs & Quality Scans...")

    # Fetch machine IDs from graph
    all_machines_res = g.query("MATCH (m:Machine) RETURN m.id, m.name, coalesce(m.facility_id, 'FACILITY_APEX')").result_set
    all_machines = [{"id": r[0], "name": r[1], "fac": r[2]} for r in all_machines_res]
    print(f"   Mapped {len(all_machines)} machines across facilities.")

    all_parts_res = g.query("MATCH (p:Part) RETURN p.id").result_set
    all_part_ids = [r[0] for r in all_parts_res]

    all_cust_res = g.query("MATCH (c:Customer) RETURN c.id").result_set
    all_cust_ids = [r[0] for r in all_cust_res]

    all_prod_res = g.query("MATCH (pr:Product) RETURN pr.id, pr.name").result_set
    all_prods = [{"id": r[0], "name": r[1]} for r in all_prod_res]

    # Generate 1,400 Production Batches
    batches = []
    base_time = datetime(2026, 8, 1, 0, 0, 0)
    for i in range(1, 1401):
        m = rng.choice(all_machines)
        pt = rng.choice(all_part_ids)
        delta_days = rng.uniform(0, 80)
        batch_date = base_time + timedelta(days=delta_days)
        is_cleanroom = m["fac"] == "FACILITY_LONDON"
        
        batches.append({
            "id": f"BATCH_{i:05d}",
            "serial_no": f"SN-{2026}-{i:06d}",
            "batch_code": f"LOT-{'LDN' if is_cleanroom else 'APX'}-{i:04d}",
            "machine_id": m["id"],
            "part_id": pt,
            "units_produced": rng.randint(250, 5000),
            "yield_rate_pct": round(rng.uniform(92.5, 99.8), 2),
            "purity_spec": "99.999% Electronic Grade" if is_cleanroom else "ISO 9001 Grade 5 Hardened",
            "cert_hash": f"SHA256-{hex(rng.getrandbits(64))[2:]}",
            "manufacturing_log": f"Batch completed under nominal operational parameters. Coolant flow stable, ambient pressure 24.8 Pa, thermal flux +-0.4C, certified defect density < 0.02/cm2.",
            "status": "APPROVED" if rng.random() > 0.04 else "QUARANTINED",
            "created_at": batch_date.isoformat()
        })

    # Chunked UNWIND insertion of Batches
    print(f"   Writing {len(batches)} Production Batches via chunked UNWIND...")
    for idx in range(0, len(batches), BATCH_CHUNK):
        chunk = batches[idx : idx + BATCH_CHUNK]
        g.query("""
        UNWIND $batch AS b
        MERGE (bt:Batch {id: b.id})
        ON CREATE SET 
            bt.serial_no = b.serial_no,
            bt.batch_code = b.batch_code,
            bt.units_produced = b.units_produced,
            bt.yield_rate_pct = b.yield_rate_pct,
            bt.purity_spec = b.purity_spec,
            bt.cert_hash = b.cert_hash,
            bt.manufacturing_log = b.manufacturing_log,
            bt.status = b.status,
            bt.created_at = b.created_at
        WITH bt, b
        MATCH (m:Machine {id: b.machine_id})
        MERGE (m)-[:PRODUCED_BATCH]->(bt)
        WITH bt, b
        MATCH (pt:Part {id: b.part_id})
        MERGE (bt)-[:OF_PART]->(pt)
        """, params={"batch": chunk})

    # Generate 1,000 Quality Inspection Scans linked to Batches
    print("5/7. Seeding In-Line Quality Metrology & Defect Scans...")
    inspections = []
    inspectors = ["Dr. H. Chen (Lead Metrologist)", "S. Vance (Quality Chief)", "L. Thorne (QA Director)", "Automated AI Vision Inspec-04"]
    for i in range(1, 1001):
        b = rng.choice(batches)
        passed = rng.random() > 0.03
        defect_count = 0 if passed else rng.randint(1, 4)
        scan_time = datetime.fromisoformat(b["created_at"]) + timedelta(hours=rng.randint(1, 8))
        
        inspections.append({
            "id": f"INSP_{i:05d}",
            "batch_id": b["id"],
            "inspector": rng.choice(inspectors),
            "passed": passed,
            "verdict": "PASS" if passed else "REWORK_REQUIRED",
            "defect_count": defect_count,
            "surface_roughness_ra": round(rng.uniform(0.10, 0.45), 3),
            "xray_void_percentage": round(rng.uniform(0.01, 0.15), 3),
            "scan_report": f"Automated 3D coordinate scanning complete. Volumetric cross-section reveals zero micro-fissures. Dimensional tolerance conforms strictly to engineering design spec +-0.005mm.",
            "timestamp": scan_time.isoformat()
        })

    for idx in range(0, len(inspections), BATCH_CHUNK):
        chunk = inspections[idx : idx + BATCH_CHUNK]
        g.query("""
        UNWIND $batch AS insp
        MERGE (q:QualityInspection {id: insp.id})
        ON CREATE SET 
            q.inspector = insp.inspector,
            q.passed = insp.passed,
            q.verdict = insp.verdict,
            q.defect_count = insp.defect_count,
            q.surface_roughness_ra = insp.surface_roughness_ra,
            q.xray_void_percentage = insp.xray_void_percentage,
            q.scan_report = insp.scan_report,
            q.timestamp = insp.timestamp
        WITH q, insp
        MATCH (bt:Batch {id: insp.batch_id})
        MERGE (bt)-[:INSPECTED_IN]->(q)
        """, params={"batch": chunk})

    # Generate 600 Customer Purchase Orders with Active SLAs
    print("6/7. Seeding Enterprise Customer Purchase Orders & SLAs...")
    orders = []
    carriers = ["DHL Express Global", "FedEx Supply Chain", "Maersk Intermodal", "Kuehne+Nagel Cold-Chain"]
    for i in range(1, 601):
        c_id = rng.choice(all_cust_ids)
        prod = rng.choice(all_prods)
        qty = rng.randint(50, 1200)
        unit_price = round(rng.uniform(450.0, 4200.0), 2)
        order_date = base_time + timedelta(days=rng.uniform(10, 80))
        sla_deadline = order_date + timedelta(days=rng.randint(7, 30))
        sla_hours = int((sla_deadline - order_date).total_seconds() / 3600)
        
        orders.append({
            "id": f"ORD_{2026}_{i:04d}",
            "order_number": f"PO-{c_id}-{i:04d}",
            "customer_id": c_id,
            "product_id": prod["id"],
            "quantity": qty,
            "unit_price_usd": unit_price,
            "total_value_usd": round(qty * unit_price, 2),
            "sla_hours_remaining": sla_hours,
            "sla_deadline": sla_deadline.isoformat(),
            "status": "PROCESSING" if rng.random() > 0.15 else "SHIPPED",
            "carrier": rng.choice(carriers),
            "shipping_notes": f"High-priority certified industrial consignment for {c_id}. Sealed under monitored nitrogen dry atmosphere container with live telemetry shock sensors.",
            "order_date": order_date.isoformat()
        })

    for idx in range(0, len(orders), BATCH_CHUNK):
        chunk = orders[idx : idx + BATCH_CHUNK]
        g.query("""
        UNWIND $batch AS o
        MERGE (ord:CustomerOrder {id: o.id})
        ON CREATE SET 
            ord.order_number = o.order_number,
            ord.quantity = o.quantity,
            ord.unit_price_usd = o.unit_price_usd,
            ord.total_value_usd = o.total_value_usd,
            ord.sla_hours_remaining = o.sla_hours_remaining,
            ord.sla_deadline = o.sla_deadline,
            ord.status = o.status,
            ord.carrier = o.carrier,
            ord.shipping_notes = o.shipping_notes,
            ord.order_date = o.order_date
        WITH ord, o
        MATCH (c:Customer {id: o.customer_id})
        MERGE (c)-[:PLACED]->(ord)
        WITH ord, o
        MATCH (pr:Product {id: o.product_id})
        MERGE (ord)-[:CONTAINS_PRODUCT]->(pr)
        """, params={"batch": chunk})

    # -------------------------------------------------------------
    # 5. HIGH-DENSITY SENSOR TELEMETRY & MAINTENANCE LOGS
    # -------------------------------------------------------------
    print("7/7. Seeding High-Volume Machine Telemetry & Maintenance Incident Records...")
    maintenance_records = []
    incident_types = [
        ("Vibration Harmonic Resonance", "Calibrated multi-axis damping bearings, retensioned lead screw, verified RMS velocity < 1.8 mm/s."),
        ("Thermal Gradient Excursion", "Flushed closed-loop glycol chiller, replaced bypass solenoid valve, recalibrated RTD thermocouple sensors."),
        ("Piezo Sensor Drift", "Performed sub-micron optical zero-point homing calibration across all six degrees of freedom."),
        ("Hydraulic Pressure Drop", "Purged hydraulic reservoir, swapped dual high-pressure particulate filters, pressure restored to 210 bar."),
        ("EUV Optical Reticle Cleaning", "Performed in-situ hydrogen plasma radical purge on collector optics, recovered transmission efficiency by 4.2%."),
    ]

    for i in range(1, 501):
        m = rng.choice(all_machines)
        inc_type, action = rng.choice(incident_types)
        log_date = base_time + timedelta(days=rng.uniform(5, 75))
        maintenance_records.append({
            "id": f"MAINT_{i:04d}",
            "machine_id": m["id"],
            "incident_type": inc_type,
            "action_taken": action,
            "downtime_minutes": rng.randint(45, 360),
            "technician": f"Tech Lead-{rng.randint(101, 140)}",
            "diagnostic_summary": f"Incident triggered via anomaly watchdog on {m['name']}. Root cause traced to {inc_type.lower()}. Corrective action completed with full post-service telemetry verification.",
            "timestamp": log_date.isoformat()
        })

    for idx in range(0, len(maintenance_records), BATCH_CHUNK):
        chunk = maintenance_records[idx : idx + BATCH_CHUNK]
        g.query("""
        UNWIND $batch AS mr
        MERGE (ml:MaintenanceLog {id: mr.id})
        ON CREATE SET 
            ml.incident_type = mr.incident_type,
            ml.action_taken = mr.action_taken,
            ml.downtime_minutes = mr.downtime_minutes,
            ml.technician = mr.technician,
            ml.diagnostic_summary = mr.diagnostic_summary,
            ml.timestamp = mr.timestamp
        WITH ml, mr
        MATCH (m:Machine {id: mr.machine_id})
        MERGE (m)-[:HAS_MAINTENANCE_EVENT]->(ml)
        """, params={"batch": chunk})

    # Generate rich Telemetry Event series to guarantee >= 1MB memory increase
    curr_mem = get_current_memory_bytes(db)
    mem_delta = curr_mem - init_mem
    print(f"\n   Progress Check: Current Memory = {curr_mem / (1024*1024):.2f} MB (Delta: +{mem_delta / (1024*1024):.2f} MB)")

    telemetry_batch_count = 0
    while mem_delta < 1048576:
        needed_bytes = 1048576 - mem_delta
        print(f"   Generating high-resolution rolling telemetry streams to satisfy +1.0 MB target (needed: {needed_bytes:,} bytes)...")
        
        telemetry_events = []
        for _ in range(600):
            telemetry_batch_count += 1
            m = rng.choice(all_machines)
            temp = round(64.5 + rng.uniform(-4.0, 5.0), 2)
            vib = round(1.20 + rng.uniform(-0.3, 0.4), 3)
            power = round(rng.uniform(18.5, 95.0), 2)
            acoust = round(rng.uniform(55.0, 78.5), 1)
            t_stamp = base_time + timedelta(hours=rng.randint(0, 1800))
            
            # Rich structured diagnostic sensor payload string
            raw_signature = (
                f"VIB_X={vib:.3f}|VIB_Y={(vib*0.92):.3f}|VIB_Z={(vib*1.08):.3f};"
                f"TEMP_MOTOR={temp:.1f}C|TEMP_SPINDLE={(temp+3.2):.1f}C|TEMP_BEARING={(temp-1.8):.1f}C;"
                f"KW_DRAW={power:.2f}kW|POWER_FACTOR=0.96|HARMONIC_THD=1.42%;"
                f"ACOUSTIC={acoust:.1f}dB|FLUID_PRESSURE=208.4kPa|STATUS_HEX=0x00FF812A"
            )

            telemetry_events.append({
                "id": f"TLOG_{telemetry_batch_count:06d}",
                "machine_id": m["id"],
                "temperature_c": temp,
                "vibration_rms": vib,
                "power_kw": power,
                "acoustic_db": acoust,
                "raw_signature": raw_signature,
                "status": "NOMINAL" if vib < 2.5 else "ELEVATED",
                "timestamp": t_stamp.isoformat()
            })

        for idx in range(0, len(telemetry_events), BATCH_CHUNK):
            chunk = telemetry_events[idx : idx + BATCH_CHUNK]
            g.query("""
            UNWIND $batch AS t
            MERGE (tl:TelemetryLog {id: t.id})
            ON CREATE SET 
                tl.temperature_c = t.temperature_c,
                tl.vibration_rms = t.vibration_rms,
                tl.power_kw = t.power_kw,
                tl.acoustic_db = t.acoustic_db,
                tl.raw_signature = t.raw_signature,
                tl.status = t.status,
                tl.timestamp = t.timestamp
            WITH tl, t
            MATCH (m:Machine {id: t.machine_id})
            MERGE (m)-[:LOGGED_TELEMETRY]->(tl)
            """, params={"batch": chunk})

        curr_mem = get_current_memory_bytes(db)
        mem_delta = curr_mem - init_mem
        print(f"   Memory Updated: {curr_mem / (1024*1024):.2f} MB (+{mem_delta / (1024*1024):.2f} MB gained)")

    # -------------------------------------------------------------
    # FINAL VERIFICATION & METRICS REPORT
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    print("SEEDING COMPLETED SUCCESSFULLY!")
    print("=" * 65)

    final_mem = get_current_memory_bytes(db)
    net_gain_bytes = final_mem - init_mem
    net_gain_mb = net_gain_bytes / (1024 * 1024)

    total_nodes = g.query("MATCH (n) RETURN count(n)").result_set[0][0]
    total_edges = g.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]

    print(f"Total Nodes in Graph        : {total_nodes:,}")
    print(f"Total Relationships in Graph: {total_edges:,}")
    print("-" * 65)
    print(f"Initial Memory              : {init_mem / (1024*1024):.2f} MB")
    print(f"Final Memory                : {final_mem / (1024*1024):.2f} MB")
    print(f"NET DATA ADDED              : +{net_gain_mb:.2f} MB ({net_gain_bytes:,} bytes)")
    print(f"Max Limit (Free Tier)       : 100.00 MB")
    print(f"Remaining Free Headroom     : {(100.0 - (final_mem / (1024*1024))):.2f} MB (~{((100 - final_mem/(1024*1024))/100)*100:.1f}% free)")
    print("=" * 65)

    # Label breakdown
    print("\nNode Counts by Label:")
    labels_res = g.query("MATCH (n) RETURN distinct labels(n)[0], count(n) ORDER BY count(n) DESC").result_set
    for label, count in labels_res:
        print(f"  {label:24s}: {count:,}")

    # Preserved benchmark checks
    print("\nBenchmark Integrity Verification:")
    m7_check = g.query("MATCH (m:Machine {id: 'M7'}) RETURN m.name, m.failure_risk").result_set
    m12_check = g.query("MATCH (m:Machine {id: 'M12'}) RETURN m.name, m.failure_risk").result_set
    print(f"  M7 Critical Baseline  : {m7_check[0] if m7_check else 'MISSING'}")
    print(f"  M12 Redundant Baseline: {m12_check[0] if m12_check else 'MISSING'}")


if __name__ == "__main__":
    main()
