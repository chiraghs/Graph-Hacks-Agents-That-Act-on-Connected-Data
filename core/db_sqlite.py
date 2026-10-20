"""core/db_sqlite.py - SQLite Factory Blueprint & Architectural Layout Database.

Separation of Concerns:
- SQLite (`data/factories.db`): Serves factory specifications, block layouts, and visual blueprint topologies.
- FalkorDB: Remains 100% UNTOUCHED as the operational graph brain for multi-hop reasoning, blast radius, live risk, and AI Cypher.
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

SQLITE_PATH = Path(__file__).resolve().parent.parent / "data" / "factories.db"


def get_sqlite_connection() -> sqlite3.Connection:
    """Returns a SQLite connection configured for row dictionaries."""
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_db():
    """Initializes SQLite schema and populates blueprint data if not present."""
    conn = get_sqlite_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS factories (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        country TEXT NOT NULL,
        facility_type TEXT NOT NULL,
        floor_area_sqm INTEGER NOT NULL,
        shifts_per_day INTEGER DEFAULT 3,
        plant_manager TEXT NOT NULL,
        operational_status TEXT DEFAULT 'ACTIVE',
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS factory_blocks (
        id TEXT PRIMARY KEY,
        factory_id TEXT NOT NULL,
        block_name TEXT NOT NULL,
        block_type TEXT NOT NULL,
        temperature_target REAL,
        humidity_target REAL,
        sqm INTEGER,
        FOREIGN KEY(factory_id) REFERENCES factories(id)
    );

    CREATE TABLE IF NOT EXISTS factory_blueprints (
        factory_id TEXT PRIMARY KEY,
        blueprint_name TEXT NOT NULL,
        layout_type TEXT NOT NULL,
        canvas_config_json TEXT NOT NULL,
        nodes_json TEXT NOT NULL,
        edges_json TEXT NOT NULL,
        FOREIGN KEY(factory_id) REFERENCES factories(id)
    );
    """)

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM factories")
    count = cursor.fetchone()[0]
    if count == 0:
        _seed_blueprints(cursor)
        conn.commit()

    conn.close()


def _seed_blueprints(cursor: sqlite3.Cursor):
    """Seeds rich factory specifications and distinct visual CAD blueprint layouts."""

    # 1. Factories
    factories = [
        (
            "PLANT_DETROIT",
            "Apex Advanced Assembly",
            "Detroit, USA",
            "United States",
            "High-Volume Heavy CNC Machining & Articulated Robotics",
            48500,
            3,
            "Marcus Vance (VP Operations)",
            "ACTIVE",
            "Primary high-output automotive powertrain & industrial robotic assembly facility with 5-axis heavy milling cells.",
        ),
        (
            "PLANT_MUNICH",
            "Bavaria Mechatronics",
            "Munich, Germany",
            "Germany",
            "Cleanroom Electronics, SMT & Mechatronic Cryogenic Valves",
            36000,
            2,
            "Dr. Elena Schneider (Plant Director)",
            "ACTIVE",
            "Specialized high-precision cleanroom facility producing cryogenic valves, smart mechatronic actuators, and SMT circuit modules.",
        ),
        (
            "PLANT_AUSTIN",
            "Silicon Hill Precision",
            "Austin, USA",
            "United States",
            "Semiconductor Tooling, Wafer Fabrication & Laser Dicing",
            42000,
            3,
            "Kavita Raman (Director of Advanced Fab)",
            "ACTIVE",
            "Ultra-cleanroom Class 100 semiconductor tooling, wafer planarization, photolithographic etching, and micro-machining fab.",
        ),
        (
            "ALL",
            "Global Enterprise Network",
            "Worldwide (Detroit, Munich, Austin)",
            "Global",
            "Enterprise Multi-Facility Connected Graph Topology",
            126500,
            3,
            "Chief Supply Chain Officer",
            "ACTIVE",
            "Multi-plant global manufacturing, warehouse buffering, and customer SLA delivery network.",
        ),
    ]

    cursor.executemany(
        """
        INSERT OR REPLACE INTO factories 
        (id, name, location, country, facility_type, floor_area_sqm, shifts_per_day, plant_manager, operational_status, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        factories,
    )

    # 2. Factory Blocks
    blocks = [
        # Detroit Blocks
        ("DET_BLK_01", "PLANT_DETROIT", "Raw Ingot Infeed & Heavy Staging", "Infeed", 20.0, 50.0, 9500),
        ("DET_BLK_02", "PLANT_DETROIT", "5-Axis Heavy CNC Machining Bay", "Machining", 21.5, 45.0, 16000),
        ("DET_BLK_03", "PLANT_DETROIT", "Robotic Articulated Assembly Cell (M7)", "Assembly", 22.0, 40.0, 12000),
        ("DET_BLK_04", "PLANT_DETROIT", "CMM Coordinate Metrology & QA", "Metrology", 20.0, 35.0, 5000),
        ("DET_BLK_05", "PLANT_DETROIT", "Final Automated Packing & AGV Docks", "Packaging", 21.0, 50.0, 6000),

        # Munich Blocks
        ("MUC_BLK_01", "PLANT_MUNICH", "Class 10,000 Clean Gowning & SMT Stores", "Infeed", 19.5, 45.0, 7000),
        ("MUC_BLK_02", "PLANT_MUNICH", "High-Speed SMT & Solder Printing Line", "Cleanroom", 20.5, 40.0, 11000),
        ("MUC_BLK_03", "PLANT_MUNICH", "Dual Cryogenic Valve Workcell (M12 & M13)", "Assembly", 20.0, 38.0, 9000),
        ("MUC_BLK_04", "PLANT_MUNICH", "10-Zone Nitrogen Reflow & Flying Probe", "Testing", 21.0, 42.0, 5500),
        ("MUC_BLK_05", "PLANT_MUNICH", "Nitrogen Vacuum Crate & Clean Dispatch", "Packaging", 20.0, 45.0, 3500),

        # Austin Blocks
        ("AUS_BLK_01", "PLANT_AUSTIN", "Crystal Silicon Ingot Storage & Lapping", "Infeed", 19.0, 35.0, 8000),
        ("AUS_BLK_02", "PLANT_AUSTIN", "Photolithographic Etching & Stepper Bay", "Cleanroom Class 100", 20.0, 30.0, 13000),
        ("AUS_BLK_03", "PLANT_AUSTIN", "UV Laser Micro-Dicing & Precision Spindle", "Micro-Machining", 20.2, 32.0, 10000),
        ("AUS_BLK_04", "PLANT_AUSTIN", "Ultrasonic Thermosonic Wire Bonding Bay", "Bonding", 20.5, 30.0, 6000),
        ("AUS_BLK_05", "PLANT_AUSTIN", "Hermetic Outfeed & Nitrogen Chamber", "Packaging", 19.5, 33.0, 5000),
    ]

    cursor.executemany(
        """
        INSERT OR REPLACE INTO factory_blocks
        (id, factory_id, block_name, block_type, temperature_target, humidity_target, sqm)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        blocks,
    )

    # 3. Factory Blueprints (Nodes & Edges Layouts)
    # -------------------------------------------------------------
    # BLUEPRINT 1: DETROIT (Heavy Linear & Robotic Assembly Cell)
    # Machines: M1, M4, M7 (Critical Alert), M10, M13, M16, M19, M22, M25
    # -------------------------------------------------------------
    detroit_nodes = [
        {"id": "DET_STORES", "name": "Raw Ingot Stores", "type": "Inventory", "bay": "Infeed Bay", "x": 20, "y": 140, "w": 180, "h": 96, "icon": "storage", "status": "HEALTHY", "spec": "AISI 4340 Alloy Bar Stock"},
        {"id": "M1", "name": "CNC Roughing Mill M1", "type": "Machine", "bay": "Bay 1 • Heavy Milling", "x": 260, "y": 60, "w": 190, "h": 100, "machine_id": "M1", "icon": "cnc", "spec": "5-Axis Heavy Spindle"},
        {"id": "M4", "name": "CNC Finisher M4", "type": "Machine", "bay": "Bay 1 • Heavy Milling", "x": 260, "y": 220, "w": 190, "h": 100, "machine_id": "M4", "icon": "cnc", "spec": "Diamond Tool Milling"},
        {"id": "M7", "name": "Assembly Robot A3 (M7)", "type": "Machine", "bay": "Bay 2 • Robotic Cell", "x": 520, "y": 60, "w": 200, "h": 105, "machine_id": "M7", "icon": "robot", "alert": "Joint-4 Bearing Wear • 94% Risk", "spec": "KUKA KR-16 Articulated Arm"},
        {"id": "M10", "name": "Annealing Furnace M10", "type": "Machine", "bay": "Bay 2 • Thermal Bay", "x": 520, "y": 220, "w": 200, "h": 100, "machine_id": "M10", "icon": "furnace", "spec": "Induction Core Annealing"},
        {"id": "M13", "name": "CMM Metrology M13", "type": "Machine", "bay": "Bay 3 • Metrology QA", "x": 780, "y": 60, "w": 190, "h": 100, "machine_id": "M13", "icon": "qa", "spec": "Zeiss 3D Optical Metrology"},
        {"id": "M16", "name": "Surface Profiler M16", "type": "Machine", "bay": "Bay 3 • Metrology QA", "x": 780, "y": 220, "w": 190, "h": 100, "machine_id": "M16", "icon": "qa", "spec": "Laser Micro-Interferometer"},
        {"id": "M19", "name": "Robotic Palletizer M19", "type": "Machine", "bay": "Bay 4 • Dispatch Bay", "x": 1040, "y": 60, "w": 190, "h": 96, "machine_id": "M19", "icon": "pallet", "spec": "Automated End-of-Line"},
        {"id": "M22", "name": "Stretch Wrapper M22", "type": "Machine", "bay": "Bay 4 • Dispatch Bay", "x": 1040, "y": 180, "w": 190, "h": 96, "machine_id": "M22", "icon": "wrapper", "spec": "Rotary Arm Film Seal"},
        {"id": "M25", "name": "AGV Dispatch Dock M25", "type": "Machine", "bay": "Bay 4 • Shipping Dock", "x": 1040, "y": 300, "w": 190, "h": 96, "machine_id": "M25", "icon": "dock", "spec": "Autonomous Mobile Tugger"},
    ]
    detroit_edges = [
        {"from": "DET_STORES", "to": "M1", "path": "M 200 170 C 230 170, 230 110, 260 110", "color": "#3987e5", "stroke": "2.0"},
        {"from": "DET_STORES", "to": "M4", "path": "M 200 170 C 230 170, 230 270, 260 270", "color": "#3987e5", "stroke": "2.0"},
        {"from": "M1", "to": "M7", "path": "M 450 110 L 520 110", "color": "#ef4444", "stroke": "2.6", "is_hot": True},
        {"from": "M4", "to": "M10", "path": "M 450 270 L 520 270", "color": "#3987e5", "stroke": "2.0"},
        {"from": "M7", "to": "M13", "path": "M 720 110 L 780 110", "color": "#ef4444", "stroke": "2.4", "is_hot": True},
        {"from": "M10", "to": "M16", "path": "M 720 270 L 780 270", "color": "#3987e5", "stroke": "2.0"},
        {"from": "M13", "to": "M19", "path": "M 970 110 L 1040 110", "color": "#10b981", "stroke": "2.0"},
        {"from": "M16", "to": "M22", "path": "M 970 270 C 1000 270, 1010 230, 1040 230", "color": "#10b981", "stroke": "2.0"},
        {"from": "M22", "to": "M25", "path": "M 1135 276 L 1135 300", "color": "#10b981", "stroke": "2.0"},
    ]

    # -------------------------------------------------------------
    # BLUEPRINT 2: MUNICH (Cleanroom Mechatronics & Dual SMT Flow)
    # Machines: M3, M6, M9, M12 (Warning/Redundant), M15, M18, M21, M24
    # -------------------------------------------------------------
    munich_nodes = [
        {"id": "MUC_STORES", "name": "SMT Component Reel Store", "type": "Inventory", "bay": "Air-Lock Infeed", "x": 20, "y": 140, "w": 180, "h": 96, "icon": "reels", "status": "HEALTHY", "spec": "Moisture-Sensitive Dry Cabinets"},
        {"id": "M3", "name": "Solder Stencil Printer M3", "type": "Machine", "bay": "Zone 1 • SMT Printing", "x": 260, "y": 60, "w": 190, "h": 100, "machine_id": "M3", "icon": "printer", "spec": "DEK NeoHorizon Laser Stencil"},
        {"id": "M6", "name": "High-Speed Chip Shooter M6", "type": "Machine", "bay": "Zone 1 • Placement", "x": 260, "y": 220, "w": 190, "h": 100, "machine_id": "M6", "icon": "chip", "spec": "Fuji NXT III (65,000 cph)"},
        {"id": "M9", "name": "Cryogenic Dispenser M9", "type": "Machine", "bay": "Zone 2 • Valve Cell", "x": 520, "y": 60, "w": 200, "h": 100, "machine_id": "M9", "icon": "dispenser", "spec": "Micro-Valve Dispensing Unit"},
        {"id": "M12", "name": "Assembly Robot B3 (M12)", "type": "Machine", "bay": "Zone 2 • Valve Cell", "x": 520, "y": 190, "w": 200, "h": 105, "machine_id": "M12", "icon": "robot", "alert": "Valve Drift • Redundant Backup M15 Online", "spec": "Cryogenic Actuator Inserter"},
        {"id": "M15", "name": "Hot-Standby Twin M15", "type": "Machine", "bay": "Zone 2 • Hot Standby", "x": 520, "y": 320, "w": 200, "h": 95, "machine_id": "M15", "icon": "backup", "status": "BACKUP", "spec": "Redundant Twin for M12"},
        {"id": "M18", "name": "10-Zone Reflow Oven M18", "type": "Machine", "bay": "Zone 3 • Thermal Tunnel", "x": 780, "y": 60, "w": 190, "h": 100, "machine_id": "M18", "icon": "oven", "spec": "Nitrogen Atmosphere Convection"},
        {"id": "M21", "name": "Flying Probe Tester M21", "type": "Machine", "bay": "Zone 3 • Metrology QA", "x": 780, "y": 220, "w": 190, "h": 100, "machine_id": "M21", "icon": "qa", "spec": "Seica 4-Axis Flying Probe"},
        {"id": "M24", "name": "Nitrogen Packager M24", "type": "Machine", "bay": "Zone 4 • Clean Dispatch", "x": 1040, "y": 140, "w": 190, "h": 100, "machine_id": "M24", "icon": "pack", "spec": "Hermetic Class 10,000 Sealer"},
    ]
    munich_edges = [
        {"from": "MUC_STORES", "to": "M3", "path": "M 200 170 C 230 170, 230 110, 260 110", "color": "#06b6d4", "stroke": "2.0"},
        {"from": "MUC_STORES", "to": "M6", "path": "M 200 170 C 230 170, 230 270, 260 270", "color": "#06b6d4", "stroke": "2.0"},
        {"from": "M3", "to": "M9", "path": "M 450 110 L 520 110", "color": "#06b6d4", "stroke": "2.0"},
        {"from": "M6", "to": "M12", "path": "M 450 270 C 480 270, 490 240, 520 240", "color": "#f59e0b", "stroke": "2.2"},
        {"from": "M6", "to": "M15", "path": "M 450 270 C 480 270, 490 365, 520 365", "color": "#10b981", "stroke": "1.8", "dashes": "4 4"},
        {"from": "M9", "to": "M18", "path": "M 720 110 L 780 110", "color": "#06b6d4", "stroke": "2.0"},
        {"from": "M12", "to": "M21", "path": "M 720 240 C 750 240, 750 270, 780 270", "color": "#06b6d4", "stroke": "2.0"},
        {"from": "M15", "to": "M21", "path": "M 720 365 C 750 365, 750 270, 780 270", "color": "#10b981", "stroke": "1.8", "dashes": "4 4"},
        {"from": "M18", "to": "M24", "path": "M 970 110 C 1000 110, 1000 190, 1040 190", "color": "#10b981", "stroke": "2.0"},
        {"from": "M21", "to": "M24", "path": "M 970 270 C 1000 270, 1000 190, 1040 190", "color": "#10b981", "stroke": "2.0"},
    ]

    # -------------------------------------------------------------
    # BLUEPRINT 3: AUSTIN (Semiconductor Cleanroom Fab Cluster Flow)
    # Machines: M2, M5, M8, M11, M14, M17, M20, M23
    # -------------------------------------------------------------
    austin_nodes = [
        {"id": "AUS_INGOT", "name": "Silicon Ingot Bay", "type": "Inventory", "bay": "Clean Infeed", "x": 20, "y": 140, "w": 180, "h": 96, "icon": "silicon", "status": "HEALTHY", "spec": "300mm Monocrystalline Silicon"},
        {"id": "M2", "name": "Wire Saw Slicer M2", "type": "Machine", "bay": "Cluster A • Ingot Saw", "x": 260, "y": 60, "w": 190, "h": 100, "machine_id": "M2", "icon": "saw", "spec": "Diamond Wire Multi-Slicing"},
        {"id": "M5", "name": "Wafer Planarizer M5", "type": "Machine", "bay": "Cluster A • CMP Lapping", "x": 260, "y": 220, "w": 190, "h": 100, "machine_id": "M5", "icon": "cmp", "spec": "Chemical-Mechanical Polishing"},
        {"id": "M8", "name": "DRIE Reactive Etcher M8", "type": "Machine", "bay": "Cluster B • Photolithography", "x": 520, "y": 60, "w": 200, "h": 100, "machine_id": "M8", "icon": "etcher", "spec": "Deep Reactive-Ion Plasma"},
        {"id": "M11", "name": "Laser Micro-Dicing M11", "type": "Machine", "bay": "Cluster B • Dicing Bay", "x": 520, "y": 220, "w": 200, "h": 100, "machine_id": "M11", "icon": "laser", "spec": "Picosecond UV Laser Dicer"},
        {"id": "M14", "name": "Tooling Spindle M14", "type": "Machine", "bay": "Cluster C • Micro-Tooling", "x": 780, "y": 60, "w": 190, "h": 100, "machine_id": "M14", "icon": "spindle", "spec": "Air-Bearing 120,000 RPM Spindle"},
        {"id": "M17", "name": "Ultrasonic Die Bonder M17", "type": "Machine", "bay": "Cluster C • Bonding", "x": 780, "y": 220, "w": 190, "h": 100, "machine_id": "M17", "icon": "bonder", "spec": "High-Density Sub-Micron Bonder"},
        {"id": "M20", "name": "Thermosonic Bonder M20", "type": "Machine", "bay": "Cluster D • Wire Bonding", "x": 1040, "y": 60, "w": 190, "h": 96, "machine_id": "M20", "icon": "wire", "spec": "Gold-Ball Micro-Interconnect"},
        {"id": "M23", "name": "Hermetic Sealer M23", "type": "Machine", "bay": "Cluster D • Clean Vacuum Outfeed", "x": 1040, "y": 210, "w": 190, "h": 96, "machine_id": "M23", "icon": "seal", "spec": "Class 100 Vacuum Nitrogen Seal"},
    ]
    austin_edges = [
        {"from": "AUS_INGOT", "to": "M2", "path": "M 200 170 C 230 170, 230 110, 260 110", "color": "#10b981", "stroke": "2.0"},
        {"from": "AUS_INGOT", "to": "M5", "path": "M 200 170 C 230 170, 230 270, 260 270", "color": "#10b981", "stroke": "2.0"},
        {"from": "M2", "to": "M8", "path": "M 450 110 L 520 110", "color": "#10b981", "stroke": "2.0"},
        {"from": "M5", "to": "M11", "path": "M 450 270 L 520 270", "color": "#10b981", "stroke": "2.0"},
        {"from": "M8", "to": "M14", "path": "M 720 110 L 780 110", "color": "#10b981", "stroke": "2.0"},
        {"from": "M11", "to": "M17", "path": "M 720 270 L 780 270", "color": "#10b981", "stroke": "2.0"},
        {"from": "M14", "to": "M20", "path": "M 970 110 L 1040 110", "color": "#10b981", "stroke": "2.0"},
        {"from": "M17", "to": "M23", "path": "M 970 270 C 1000 270, 1000 260, 1040 260", "color": "#10b981", "stroke": "2.0"},
        {"from": "M20", "to": "M23", "path": "M 1135 156 L 1135 210", "color": "#10b981", "stroke": "2.0"},
    ]

    # -------------------------------------------------------------
    # BLUEPRINT 4: ALL PLANTS (Global Multi-Facility Macro Graph)
    # Connects: Suppliers -> 3 Manufacturing Plants -> 6 Warehouses -> 40 Customers
    # -------------------------------------------------------------
    all_nodes = [
        {"id": "GLOBAL_SUPPLIERS", "name": "Global Suppliers (15)", "type": "NetworkHub", "bay": "Tier-1 Supply Network", "x": 20, "y": 140, "w": 200, "h": 110, "icon": "suppliers", "spec": "15 Global Vendors across NA, EU, Asia"},
        {"id": "PLANT_DETROIT", "name": "Apex Advanced Assembly", "type": "Plant", "bay": "Detroit Facility", "x": 300, "y": 40, "w": 210, "h": 90, "alert": "1 Critical Alert (M7)", "spec": "9 CNC Units • ECU-200 Line"},
        {"id": "PLANT_MUNICH", "name": "Bavaria Mechatronics", "type": "Plant", "bay": "Munich Facility", "x": 300, "y": 160, "w": 210, "h": 90, "alert": "1 Warning Alert (M12 Backup Online)", "spec": "8 Mechatronic Units • SH-40 Line"},
        {"id": "PLANT_AUSTIN", "name": "Silicon Hill Precision", "type": "Plant", "bay": "Austin Facility", "x": 300, "y": 280, "w": 210, "h": 90, "status": "HEALTHY", "spec": "8 Fab Units • Semiconductor Micro-Tooling"},
        {"id": "GLOBAL_WAREHOUSES", "name": "Regional Hubs (6)", "type": "NetworkHub", "bay": "Warehouse Buffers", "x": 600, "y": 140, "w": 210, "h": 110, "icon": "warehouse", "spec": "Chicago, Newark, Long Beach, Dallas, Frankfurt, Gothenburg"},
        {"id": "GLOBAL_CUSTOMERS", "name": "Enterprise Customers (40)", "type": "NetworkHub", "bay": "SLA Fulfillment", "x": 900, "y": 140, "w": 210, "h": 110, "icon": "customers", "spec": "10 Strategic, 15 Enterprise, 15 Standard"},
    ]
    all_edges = [
        {"from": "GLOBAL_SUPPLIERS", "to": "PLANT_DETROIT", "path": "M 220 170 C 260 170, 260 85, 300 85", "color": "#a855f7", "stroke": "2.2"},
        {"from": "GLOBAL_SUPPLIERS", "to": "PLANT_MUNICH", "path": "M 220 195 L 300 205", "color": "#a855f7", "stroke": "2.2"},
        {"from": "GLOBAL_SUPPLIERS", "to": "PLANT_AUSTIN", "path": "M 220 220 C 260 220, 260 325, 300 325", "color": "#a855f7", "stroke": "2.2"},
        {"from": "PLANT_DETROIT", "to": "GLOBAL_WAREHOUSES", "path": "M 510 85 C 550 85, 560 170, 600 170", "color": "#ef4444", "stroke": "2.4", "is_hot": True},
        {"from": "PLANT_MUNICH", "to": "GLOBAL_WAREHOUSES", "path": "M 510 205 L 600 195", "color": "#06b6d4", "stroke": "2.2"},
        {"from": "PLANT_AUSTIN", "to": "GLOBAL_WAREHOUSES", "path": "M 510 325 C 550 325, 560 220, 600 220", "color": "#10b981", "stroke": "2.2"},
        {"from": "GLOBAL_WAREHOUSES", "to": "GLOBAL_CUSTOMERS", "path": "M 810 195 L 900 195", "color": "#10b981", "stroke": "2.5"},
    ]

    blueprints = [
        ("PLANT_DETROIT", "Apex Detroit Powertrain & Heavy Robotic Cell", "linear_robotic_cell", json.dumps({"panX": 40, "panY": 80, "zoom": 0.82}), json.dumps(detroit_nodes), json.dumps(detroit_edges)),
        ("PLANT_MUNICH", "Bavaria Munich SMT & Cryogenic Valve Cleanroom", "cleanroom_smt_flow", json.dumps({"panX": 40, "panY": 80, "zoom": 0.82}), json.dumps(munich_nodes), json.dumps(munich_edges)),
        ("PLANT_AUSTIN", "Silicon Hill Austin Semiconductor Wafer Fab", "semiconductor_fab_cluster", json.dumps({"panX": 40, "panY": 80, "zoom": 0.82}), json.dumps(austin_nodes), json.dumps(austin_edges)),
        ("ALL", "Global Enterprise Connected Supply Chain Network", "macro_supply_chain", json.dumps({"panX": 40, "panY": 120, "zoom": 0.85}), json.dumps(all_nodes), json.dumps(all_edges)),
    ]

    cursor.executemany(
        """
        INSERT OR REPLACE INTO factory_blueprints
        (factory_id, blueprint_name, layout_type, canvas_config_json, nodes_json, edges_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        blueprints,
    )


def get_all_factories() -> List[Dict[str, Any]]:
    """Retrieves all factories from SQLite."""
    init_sqlite_db()
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM factories ORDER BY id")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_factory_by_id(factory_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves factory details and its architectural blocks from SQLite."""
    init_sqlite_db()
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM factories WHERE id = ?", (factory_id,))
    f_row = cursor.fetchone()
    if not f_row:
        conn.close()
        return None

    factory = dict(f_row)
    cursor.execute("SELECT * FROM factory_blocks WHERE factory_id = ? ORDER BY id", (factory_id,))
    factory["blocks"] = [dict(b) for b in cursor.fetchall()]
    conn.close()
    return factory


def get_factory_blueprint(factory_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves visual CAD blueprint topology (nodes, edges, config) for a specific plant."""
    init_sqlite_db()
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM factory_blueprints WHERE factory_id = ?", (factory_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    data = dict(row)
    data["canvas_config"] = json.loads(data["canvas_config_json"])
    data["nodes"] = json.loads(data["nodes_json"])
    data["edges"] = json.loads(data["edges_json"])
    del data["canvas_config_json"]
    del data["nodes_json"]
    del data["edges_json"]
    return data
