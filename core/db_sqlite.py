"""core/db_sqlite.py - SQLite Factory & Facility Blueprint Database.

Separation of Concerns:
- SQLite (`data/factories.db`): Serves multi-facility registry, plant blocks, and visual blueprint topologies.
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
    CREATE TABLE IF NOT EXISTS facilities (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        city TEXT NOT NULL,
        country TEXT NOT NULL,
        facility_type TEXT NOT NULL,
        total_area_sqm INTEGER NOT NULL,
        director TEXT NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS factories (
        id TEXT PRIMARY KEY,
        facility_id TEXT NOT NULL DEFAULT 'FACILITY_APEX',
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        country TEXT NOT NULL,
        facility_type TEXT NOT NULL,
        floor_area_sqm INTEGER NOT NULL,
        shifts_per_day INTEGER DEFAULT 3,
        plant_manager TEXT NOT NULL,
        operational_status TEXT DEFAULT 'ACTIVE',
        description TEXT,
        FOREIGN KEY(facility_id) REFERENCES facilities(id)
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

    # Check if facility table has columns or if we need migration
    cursor.execute("PRAGMA table_info(factories)")
    col_names = [r[1] for r in cursor.fetchall()]
    if "facility_id" not in col_names:
        cursor.execute("ALTER TABLE factories ADD COLUMN facility_id TEXT NOT NULL DEFAULT 'FACILITY_APEX'")

    # Check if London facility exists
    cursor.execute("SELECT COUNT(*) FROM facilities WHERE id = 'FACILITY_LONDON'")
    has_london = cursor.fetchone()[0]
    if has_london == 0:
        _seed_blueprints(cursor)
        conn.commit()

    conn.close()


def _seed_blueprints(cursor: sqlite3.Cursor):
    """Seeds rich facilities, factory specifications, and distinct visual CAD blueprint layouts."""

    # 1. Facilities (Top-Level Units)
    facilities = [
        (
            "FACILITY_APEX",
            "Apex Global Manufacturing Network",
            "Detroit, MI, USA & Global",
            "United States / Global",
            "Powertrain Machining, Mechatronics & Precision Tooling",
            126500,
            "Marcus Vance (Chief Supply Chain Officer)",
            "Global multi-site enterprise network spanning heavy machining in Detroit, cleanroom mechatronics in Munich, and precision fabrication in Austin.",
        ),
        (
            "FACILITY_LONDON",
            "Thames Nanotech Semiconductor Foundry",
            "London, United Kingdom",
            "United Kingdom",
            "ISO Class 4 Cleanroom • Semiconductor Wafer Fab & Micro-Packaging",
            54000,
            "Prof. Alistair Finch (Director of Nanofabrication)",
            "Integrated London semiconductor unit housing 2 co-located production plants (Line Alpha Wafer Fab & Line Beta Packaging) feeding a shared final unit testing & cleanroom dispatch facility.",
        ),
    ]

    cursor.executemany(
        """
        INSERT OR REPLACE INTO facilities 
        (id, name, city, country, facility_type, total_area_sqm, director, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        facilities,
    )

    # 2. Factories / Plants
    factories = [
        # Apex Facility Plants
        (
            "PLANT_DETROIT",
            "FACILITY_APEX",
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
            "FACILITY_APEX",
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
            "FACILITY_APEX",
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
            "FACILITY_APEX",
            "Apex Global Enterprise Network",
            "Worldwide (Detroit, Munich, Austin)",
            "Global",
            "Enterprise Multi-Facility Connected Graph Topology",
            126500,
            3,
            "Chief Supply Chain Officer",
            "ACTIVE",
            "Multi-plant global manufacturing, warehouse buffering, and customer SLA delivery network.",
        ),
        # London Facility Plants (2 Lines leading to one unit facility)
        (
            "PLANT_LONDON_FAB",
            "FACILITY_LONDON",
            "Thames Cleanroom Fab Alpha",
            "London, United Kingdom",
            "United Kingdom",
            "Plant 1: Front-End Wafer Lithography & Plasma Etch",
            28000,
            3,
            "Dr. Oliver Ward (Lead Nanofabrication)",
            "ACTIVE",
            "ISO Class 4 ultra-cleanroom front-end line: Diamond wire ingot slicing, CMP planarization, EUV photolithography, and atomic layer CVD deposition.",
        ),
        (
            "PLANT_LONDON_PKG",
            "FACILITY_LONDON",
            "Thames Packaging Beta",
            "London, United Kingdom",
            "United Kingdom",
            "Plant 2: Back-End Micro-Packaging & Laser Dicing",
            26000,
            3,
            "Rachel Thorne (Head of Packaging Operations)",
            "ACTIVE",
            "Sub-micron picosecond laser wafer dicing, high-speed eutectic die attach, gold wire bonding, and cryogenic hermetic vacuum encapsulation.",
        ),
        (
            "PLANT_LONDON_ALL",
            "FACILITY_LONDON",
            "Thames Semiconductor Foundry (Full Unit)",
            "London, United Kingdom",
            "United Kingdom",
            "Integrated London Semiconductor Unit (2 Lines → 1 Unit Facility)",
            54000,
            3,
            "Prof. Alistair Finch (Director of Nanofabrication)",
            "ACTIVE",
            "Complete London cleanroom facility showing Line Alpha (Wafer Fab) and Line Beta (Micro-Packaging) both converging into the shared Unit Final QC & Cleanroom Dispatch Bay.",
        ),
    ]

    cursor.executemany(
        """
        INSERT OR REPLACE INTO factories 
        (id, facility_id, name, location, country, facility_type, floor_area_sqm, shifts_per_day, plant_manager, operational_status, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        factories,
    )

    # 3. Factory Blocks for London
    blocks = [
        ("BLK_LDN_FAB_1", "PLANT_LONDON_FAB", "Class 10 Photolithography Bay", "CLEANROOM_ISO4", 20.0, 42.0, 12000),
        ("BLK_LDN_FAB_2", "PLANT_LONDON_FAB", "Plasma Etch & CVD Epitaxy Cell", "CLEANROOM_ISO4", 20.5, 40.0, 16000),
        ("BLK_LDN_PKG_1", "PLANT_LONDON_PKG", "Laser Micro-Dicing Bay", "CLEANROOM_ISO5", 21.0, 45.0, 11000),
        ("BLK_LDN_PKG_2", "PLANT_LONDON_PKG", "Thermosonic Wire Bonder Cell", "CLEANROOM_ISO5", 21.0, 44.0, 15000),
        ("BLK_LDN_UNIT_1", "PLANT_LONDON_ALL", "Unit Final Inspection & Quantum Prober", "METROLOGY_ISO4", 20.0, 40.0, 8000),
        ("BLK_LDN_UNIT_2", "PLANT_LONDON_ALL", "Airlock Nitrogen Freight Dispatch", "LOGISTICS", 22.0, 48.0, 6000),
    ]

    cursor.executemany(
        """
        INSERT OR REPLACE INTO factory_blocks
        (id, factory_id, block_name, block_type, temperature_target, humidity_target, sqm)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        blocks,
    )

    # 4. Blueprints
    # -------------------------------------------------------------
    # DETROIT BLUEPRINT
    # -------------------------------------------------------------
    detroit_nodes = [
        {"id": "DET_STORES", "name": "Raw Steel Billet Storage", "type": "Inventory", "bay": "Infeed Bay A", "x": 20, "y": 140, "w": 180, "h": 96, "icon": "inventory", "status": "HEALTHY", "spec": "Grade 4140 Chrome-Moly Forgings"},
        {"id": "M1", "name": "CNC Milling Cell M1", "type": "Machine", "bay": "Cell 1 • Heavy Roughing", "x": 240, "y": 60, "w": 190, "h": 100, "machine_id": "M1", "icon": "cnc", "spec": "Mazak 5-Axis Variaxis i-800"},
        {"id": "M4", "name": "Deep Boring Lathe M4", "type": "Machine", "bay": "Cell 1 • Cylindrical Bore", "x": 240, "y": 220, "w": 190, "h": 100, "machine_id": "M4", "icon": "lathe", "spec": "Okuma LB3000 EX-II CNC Lathe"},
        {"id": "M7", "name": "Assembly Robot A3 (M7)", "type": "Machine", "bay": "Cell 2 • Robotic Powertrain", "x": 480, "y": 60, "w": 200, "h": 105, "machine_id": "M7", "icon": "robot", "alert": "Spindle Bearing Wear (Risk 94%)", "spec": "KUKA KR 500 Titan Heavy Robot"},
        {"id": "M10", "name": "Precision Grinder M10", "type": "Machine", "bay": "Cell 2 • Tolerance Finish", "x": 480, "y": 220, "w": 200, "h": 100, "machine_id": "M10", "icon": "grinder", "spec": "Studer S33 Precision Grinder"},
        {"id": "M13", "name": "Deburring Cell M13", "type": "Machine", "bay": "Cell 3 • Edge Finishing", "x": 720, "y": 60, "w": 190, "h": 100, "machine_id": "M13", "icon": "deburr", "spec": "FANUC M-20iB Robotic Deburrer"},
        {"id": "M16", "name": "Ultrasonic Wash M16", "type": "Machine", "bay": "Cell 3 • Solvent Cleaning", "x": 720, "y": 220, "w": 190, "h": 100, "machine_id": "M16", "icon": "wash", "spec": "Amsonic 4-Stage Degreasing"},
        {"id": "M19", "name": "CMM Metrology M19", "type": "Machine", "bay": "Cell 4 • Quality Assurance", "x": 960, "y": 60, "w": 190, "h": 100, "machine_id": "M19", "icon": "cmm", "spec": "Zeiss Prismo Ultra-Accurate CMM"},
        {"id": "M22", "name": "Powertrain Dyno M22", "type": "Machine", "bay": "Cell 4 • Load Testing", "x": 960, "y": 220, "w": 190, "h": 100, "machine_id": "M22", "icon": "dyno", "spec": "AVL 500kW Transient Dynamometer"},
        {"id": "M25", "name": "Crating Robot M25", "type": "Machine", "bay": "Outfeed Bay • Packaging", "x": 1200, "y": 140, "w": 190, "h": 100, "machine_id": "M25", "icon": "crate", "spec": "ABB IRB 6700 Automated Packer"},
    ]
    detroit_edges = [
        {"from": "DET_STORES", "to": "M1", "path": "M 200 170 C 220 170, 220 110, 240 110", "color": "#3987e5", "stroke": "2.0"},
        {"from": "DET_STORES", "to": "M4", "path": "M 200 170 C 220 170, 220 270, 240 270", "color": "#3987e5", "stroke": "2.0"},
        {"from": "M1", "to": "M7", "path": "M 430 110 L 480 110", "color": "#ef4444", "stroke": "2.4", "is_hot": True},
        {"from": "M4", "to": "M10", "path": "M 430 270 L 480 270", "color": "#3987e5", "stroke": "2.0"},
        {"from": "M7", "to": "M13", "path": "M 680 110 L 720 110", "color": "#ef4444", "stroke": "2.4", "is_hot": True},
        {"from": "M10", "to": "M16", "path": "M 680 270 L 720 270", "color": "#3987e5", "stroke": "2.0"},
        {"from": "M13", "to": "M19", "path": "M 910 110 L 960 110", "color": "#3987e5", "stroke": "2.0"},
        {"from": "M16", "to": "M22", "path": "M 910 270 L 960 270", "color": "#3987e5", "stroke": "2.0"},
        {"from": "M19", "to": "M25", "path": "M 1150 110 C 1175 110, 1175 190, 1200 190", "color": "#10b981", "stroke": "2.0"},
        {"from": "M22", "to": "M25", "path": "M 1150 270 C 1175 270, 1175 190, 1200 190", "color": "#10b981", "stroke": "2.0"},
    ]

    # -------------------------------------------------------------
    # MUNICH BLUEPRINT
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
    # AUSTIN BLUEPRINT
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
    # ALL PLANTS (Apex Global Macro Graph)
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

    # -------------------------------------------------------------
    # BLUEPRINT 5: LONDON PLANT 1 (Thames Cleanroom Fab Alpha - Wafer Litho)
    # -------------------------------------------------------------
    london_fab_nodes = [
        {"id": "LDN_INGOT", "name": "300mm Silicon Ingot Vault", "type": "Inventory", "bay": "Zone 1 • Raw Infeed", "x": 40, "y": 140, "w": 190, "h": 96, "icon": "silicon", "status": "HEALTHY", "spec": "99.9999999% Pure Monocrystalline Silicon"},
        {"id": "LDN-SLI-01", "name": "Diamond Wire Slicer Alpha", "type": "Machine", "bay": "Zone 2 • Ingot Slicing", "x": 280, "y": 60, "w": 190, "h": 100, "machine_id": "LDN_M1", "icon": "saw", "spec": "Meyer Burger Diamond Multi-Wire Slicer"},
        {"id": "LDN-CMP-02", "name": "Nanotech CMP Planarizer", "type": "Machine", "bay": "Zone 2 • Chemical-Mechanical Polishing", "x": 280, "y": 220, "w": 190, "h": 100, "machine_id": "LDN_M2", "icon": "cmp", "spec": "Ebara CMP Double-Sided Polisher"},
        {"id": "LDN-EUV-03", "name": "Extreme UV Litho Stepper", "type": "Machine", "bay": "Zone 3 • ISO Class 3 Cleanroom", "x": 540, "y": 60, "w": 200, "h": 100, "machine_id": "LDN_M3", "icon": "laser", "spec": "ASML Twinscan 13.5nm High-NA EUV"},
        {"id": "LDN-RIE-04", "name": "Deep Reactive-Ion Etcher", "type": "Machine", "bay": "Zone 3 • Plasma Patterning", "x": 540, "y": 220, "w": 200, "h": 100, "machine_id": "LDN_M4", "icon": "etcher", "spec": "Lam Research Cryogenic Bosch DRIE"},
        {"id": "LDN-CVD-05", "name": "Atomic Layer CVD Chamber", "type": "Machine", "bay": "Zone 4 • Thin-Film Epitaxy", "x": 800, "y": 140, "w": 200, "h": 100, "machine_id": "LDN_M5", "icon": "reactor", "spec": "Applied Materials Endura ALD/CVD"},
        {"id": "LDN_WAFER_VAULT", "name": "Cassette Wafer Vault", "type": "Inventory", "bay": "Clean Outfeed", "x": 1060, "y": 140, "w": 190, "h": 96, "icon": "cassette", "status": "HEALTHY", "spec": "Automated Nitrogen FOUP Buffer System"},
    ]
    london_fab_edges = [
        {"from": "LDN_INGOT", "to": "LDN-SLI-01", "path": "M 230 170 C 255 170, 255 110, 280 110", "color": "#06b6d4", "stroke": "2.0"},
        {"from": "LDN_INGOT", "to": "LDN-CMP-02", "path": "M 230 170 C 255 170, 255 270, 280 270", "color": "#06b6d4", "stroke": "2.0"},
        {"from": "LDN-SLI-01", "to": "LDN-EUV-03", "path": "M 470 110 L 540 110", "color": "#06b6d4", "stroke": "2.0"},
        {"from": "LDN-CMP-02", "to": "LDN-RIE-04", "path": "M 470 270 L 540 270", "color": "#06b6d4", "stroke": "2.0"},
        {"from": "LDN-EUV-03", "to": "LDN-CVD-05", "path": "M 740 110 C 770 110, 770 190, 800 190", "color": "#06b6d4", "stroke": "2.0"},
        {"from": "LDN-RIE-04", "to": "LDN-CVD-05", "path": "M 740 270 C 770 270, 770 190, 800 190", "color": "#06b6d4", "stroke": "2.0"},
        {"from": "LDN-CVD-05", "to": "LDN_WAFER_VAULT", "path": "M 1000 190 L 1060 190", "color": "#10b981", "stroke": "2.2"},
    ]

    # -------------------------------------------------------------
    # BLUEPRINT 6: LONDON PLANT 2 (Thames Packaging Beta - Die Attach & Packaging)
    # -------------------------------------------------------------
    london_pkg_nodes = [
        {"id": "LDN_WAFER_IN", "name": "FOUP Cassette Infeed Bay", "type": "Inventory", "bay": "Zone 1 • Wafer Dock", "x": 40, "y": 140, "w": 190, "h": 96, "icon": "cassette", "status": "HEALTHY", "spec": "Sealed FOUP Nitrogen Cassette Interface"},
        {"id": "LDN-DCE-01", "name": "Picosecond Laser Dicer", "type": "Machine", "bay": "Zone 2 • Laser Singulation", "x": 280, "y": 60, "w": 190, "h": 100, "machine_id": "LDN_M6", "icon": "laser", "spec": "DISCO DFL7362 Picosecond UV Stealth Dicer"},
        {"id": "LDN-ATT-02", "name": "Eutectic Die Attach Beta", "type": "Machine", "bay": "Zone 2 • High-Speed Mount", "x": 280, "y": 220, "w": 190, "h": 100, "machine_id": "LDN_M7", "icon": "mount", "spec": "Besi Datacon 8800 FC Ultra Die Bonder"},
        {"id": "LDN-BND-03", "name": "Ultra-Fine Pitch Wire Bonder", "type": "Machine", "bay": "Zone 3 • Gold/Copper Interconnect", "x": 540, "y": 60, "w": 200, "h": 100, "machine_id": "LDN_M8", "icon": "wire", "spec": "Kulicke & Soffa PowerSeries Elite Bonder"},
        {"id": "LDN-ENC-04", "name": "Hermetic Vacuum Sealer", "type": "Machine", "bay": "Zone 3 • Cryogenic Packaging", "x": 540, "y": 220, "w": 200, "h": 100, "machine_id": "LDN_M9", "icon": "seal", "spec": "SST Vacuum Reflow & Sealing System"},
        {"id": "LDN-XRY-05", "name": "3D CT X-Ray Metrology", "type": "Machine", "bay": "Zone 4 • Non-Destructive QC", "x": 800, "y": 140, "w": 200, "h": 100, "machine_id": "LDN_M10", "icon": "xray", "spec": "Nikon Metrology XT H 225 Nanofocus"},
        {"id": "LDN_PKG_OUT", "name": "Shielded Component Outfeed", "type": "Inventory", "bay": "Clean Outfeed", "x": 1060, "y": 140, "w": 190, "h": 96, "icon": "pack", "status": "HEALTHY", "spec": "Electrostatic Antistatic Tray Dispatch"},
    ]
    london_pkg_edges = [
        {"from": "LDN_WAFER_IN", "to": "LDN-DCE-01", "path": "M 230 170 C 255 170, 255 110, 280 110", "color": "#10b981", "stroke": "2.0"},
        {"from": "LDN_WAFER_IN", "to": "LDN-ATT-02", "path": "M 230 170 C 255 170, 255 270, 280 270", "color": "#10b981", "stroke": "2.0"},
        {"from": "LDN-DCE-01", "to": "LDN-BND-03", "path": "M 470 110 L 540 110", "color": "#10b981", "stroke": "2.0"},
        {"from": "LDN-ATT-02", "to": "LDN-ENC-04", "path": "M 470 270 L 540 270", "color": "#10b981", "stroke": "2.0"},
        {"from": "LDN-BND-03", "to": "LDN-XRY-05", "path": "M 740 110 C 770 110, 770 190, 800 190", "color": "#10b981", "stroke": "2.0"},
        {"from": "LDN-ENC-04", "to": "LDN-XRY-05", "path": "M 740 270 C 770 270, 770 190, 800 190", "color": "#10b981", "stroke": "2.0"},
        {"from": "LDN-XRY-05", "to": "LDN_PKG_OUT", "path": "M 1000 190 L 1060 190", "color": "#10b981", "stroke": "2.2"},
    ]

    # -------------------------------------------------------------
    # BLUEPRINT 7: LONDON ALL PLANTS (2 Plants Leading to 1 Unit Facility)
    # -------------------------------------------------------------
    london_all_nodes = [
        # Infeed
        {"id": "LDN_STORES", "name": "London Clean Infeed Vault", "type": "Inventory", "bay": "Vault Infeed", "x": 20, "y": 190, "w": 180, "h": 110, "icon": "vault", "status": "HEALTHY", "spec": "Dual Infeed: Silicon Ingots & Substrates"},
        
        # Plant 1: Line Alpha (Front-End Litho & Etch) - Top Row
        {"id": "LDN-SLI-01", "name": "Diamond Wire Slicer (Line Alpha)", "type": "Machine", "bay": "Plant 1 • Wafer Fab", "x": 230, "y": 60, "w": 190, "h": 96, "machine_id": "LDN_M1", "spec": "Wafer Saw • 100nm Slicing"},
        {"id": "LDN-EUV-03", "name": "EUV Photolithography (Line Alpha)", "type": "Machine", "bay": "Plant 1 • Wafer Fab", "x": 445, "y": 60, "w": 190, "h": 96, "machine_id": "LDN_M3", "spec": "ASML 13.5nm EUV Litho"},
        {"id": "LDN-RIE-04", "name": "Deep Reactive Etcher (Line Alpha)", "type": "Machine", "bay": "Plant 1 • Wafer Fab", "x": 660, "y": 60, "w": 190, "h": 96, "machine_id": "LDN_M4", "spec": "Plasma Etch Bosch Process"},
        {"id": "LDN-CVD-05", "name": "ALD Epitaxy Chamber (Line Alpha)", "type": "Machine", "bay": "Plant 1 • Wafer Fab", "x": 875, "y": 60, "w": 190, "h": 96, "machine_id": "LDN_M5", "spec": "Atomic Thin-Film Deposition"},

        # Plant 2: Line Beta (Back-End Micro-Packaging) - Bottom Row
        {"id": "LDN-DCE-01", "name": "Laser Wafer Dicer (Line Beta)", "type": "Machine", "bay": "Plant 2 • Packaging", "x": 230, "y": 320, "w": 190, "h": 96, "machine_id": "LDN_M6", "spec": "Picosecond UV Laser Singulation"},
        {"id": "LDN-ATT-02", "name": "Eutectic Die Attach (Line Beta)", "type": "Machine", "bay": "Plant 2 • Packaging", "x": 445, "y": 320, "w": 190, "h": 96, "machine_id": "LDN_M7", "spec": "Sub-Micron High-Speed Mount"},
        {"id": "LDN-BND-03", "name": "Fine Wire Bonder (Line Beta)", "type": "Machine", "bay": "Plant 2 • Packaging", "x": 660, "y": 320, "w": 190, "h": 96, "machine_id": "LDN_M8", "spec": "Gold-Ball Interconnect Cell"},
        {"id": "LDN-ENC-04", "name": "Cryo Vacuum Sealer (Line Beta)", "type": "Machine", "bay": "Plant 2 • Packaging", "x": 875, "y": 320, "w": 190, "h": 96, "machine_id": "LDN_M9", "spec": "Class 10 Hermetic Seal"},

        # SHARED UNIT FACILITY: Both lines converge here!
        {"id": "LDN-UNIT-QC", "name": "Unit Final Cleanroom Inspection Bay", "type": "UnitFacility", "bay": "London Shared Unit Facility", "x": 1100, "y": 140, "w": 220, "h": 130, "icon": "unit_facility", "spec": "Shared Unit Facility • Quantum Prober & Automated CT Metrology", "status": "HEALTHY"},
        {"id": "LDN-UNIT-DISPATCH", "name": "Airlock Freight Dispatch Bay", "type": "Dispatch", "bay": "Unit Dispatch Bay", "x": 1100, "y": 330, "w": 220, "h": 96, "icon": "dispatch", "spec": "Direct Air Cargo to Cambridge & European Foundries", "status": "HEALTHY"},
    ]
    london_all_edges = [
        # Infeed to Plant 1 and Plant 2
        {"from": "LDN_STORES", "to": "LDN-SLI-01", "path": "M 200 220 C 215 220, 215 108, 230 108", "color": "#06b6d4", "stroke": "2.2"},
        {"from": "LDN_STORES", "to": "LDN-DCE-01", "path": "M 200 260 C 215 260, 215 368, 230 368", "color": "#10b981", "stroke": "2.2"},

        # Plant 1: Line Alpha internal flow
        {"from": "LDN-SLI-01", "to": "LDN-EUV-03", "path": "M 420 108 L 445 108", "color": "#06b6d4", "stroke": "2.0"},
        {"from": "LDN-EUV-03", "to": "LDN-RIE-04", "path": "M 635 108 L 660 108", "color": "#06b6d4", "stroke": "2.0"},
        {"from": "LDN-RIE-04", "to": "LDN-CVD-05", "path": "M 850 108 L 875 108", "color": "#06b6d4", "stroke": "2.0"},

        # Plant 2: Line Beta internal flow
        {"from": "LDN-DCE-01", "to": "LDN-ATT-02", "path": "M 420 368 L 445 368", "color": "#10b981", "stroke": "2.0"},
        {"from": "LDN-ATT-02", "to": "LDN-BND-03", "path": "M 635 368 L 660 368", "color": "#10b981", "stroke": "2.0"},
        {"from": "LDN-BND-03", "to": "LDN-ENC-04", "path": "M 850 368 L 875 368", "color": "#10b981", "stroke": "2.0"},

        # CONVERGENCE TO SHARED UNIT FACILITY! Both lines lead into LDN-UNIT-QC
        {"from": "LDN-CVD-05", "to": "LDN-UNIT-QC", "path": "M 1065 108 C 1085 108, 1085 180, 1100 180", "color": "#06b6d4", "stroke": "2.6"},
        {"from": "LDN-ENC-04", "to": "LDN-UNIT-QC", "path": "M 1065 368 C 1085 368, 1085 230, 1100 230", "color": "#10b981", "stroke": "2.6"},

        # Shared Unit Facility to Dispatch Bay
        {"from": "LDN-UNIT-QC", "to": "LDN-UNIT-DISPATCH", "path": "M 1210 270 L 1210 330", "color": "#a855f7", "stroke": "2.4"},
    ]

    blueprints = [
        ("PLANT_DETROIT", "Apex Detroit Powertrain & Heavy Robotic Cell", "linear_robotic_cell", json.dumps({"panX": 40, "panY": 80, "zoom": 0.82}), json.dumps(detroit_nodes), json.dumps(detroit_edges)),
        ("PLANT_MUNICH", "Bavaria Munich SMT & Cryogenic Valve Cleanroom", "cleanroom_smt_flow", json.dumps({"panX": 40, "panY": 80, "zoom": 0.82}), json.dumps(munich_nodes), json.dumps(munich_edges)),
        ("PLANT_AUSTIN", "Silicon Hill Austin Semiconductor Wafer Fab", "semiconductor_fab_cluster", json.dumps({"panX": 40, "panY": 80, "zoom": 0.82}), json.dumps(austin_nodes), json.dumps(austin_edges)),
        ("ALL", "Global Enterprise Connected Supply Chain Network", "macro_supply_chain", json.dumps({"panX": 40, "panY": 120, "zoom": 0.85}), json.dumps(all_nodes), json.dumps(all_edges)),
        ("PLANT_LONDON_FAB", "Thames London Cleanroom Fab Alpha (Wafer Lithography & Etch)", "cleanroom_wafer_fab", json.dumps({"panX": 40, "panY": 80, "zoom": 0.82}), json.dumps(london_fab_nodes), json.dumps(london_fab_edges)),
        ("PLANT_LONDON_PKG", "Thames London Packaging Beta (Die Attach & Wire Bonder)", "cleanroom_micro_packaging", json.dumps({"panX": 40, "panY": 80, "zoom": 0.82}), json.dumps(london_pkg_nodes), json.dumps(london_pkg_edges)),
        ("PLANT_LONDON_ALL", "London Semiconductor Foundry (2 Lines Leading to 1 Unit Facility)", "two_plants_one_unit_facility", json.dumps({"panX": 40, "panY": 60, "zoom": 0.78}), json.dumps(london_all_nodes), json.dumps(london_all_edges)),
    ]

    cursor.executemany(
        """
        INSERT OR REPLACE INTO factory_blueprints
        (factory_id, blueprint_name, layout_type, canvas_config_json, nodes_json, edges_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        blueprints,
    )


def get_all_facilities() -> List[Dict[str, Any]]:
    """Retrieves all top-level facilities along with their nested plants from SQLite."""
    init_sqlite_db()
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM facilities ORDER BY id")
    facilities = [dict(r) for r in cursor.fetchall()]

    for f in facilities:
        cursor.execute("SELECT * FROM factories WHERE facility_id = ? ORDER BY id", (f["id"],))
        f["plants"] = [dict(p) for p in cursor.fetchall()]

    conn.close()
    return facilities


def get_facility_by_id(facility_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single facility and its constituent plants from SQLite."""
    init_sqlite_db()
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM facilities WHERE id = ?", (facility_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    facility = dict(row)
    cursor.execute("SELECT * FROM factories WHERE facility_id = ? ORDER BY id", (facility_id,))
    facility["plants"] = [dict(p) for p in cursor.fetchall()]
    conn.close()
    return facility


def get_all_factories(facility_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all factories/plants from SQLite, optionally filtered by facility_id."""
    init_sqlite_db()
    conn = get_sqlite_connection()
    cursor = conn.cursor()
    if facility_id:
        cursor.execute("SELECT * FROM factories WHERE facility_id = ? ORDER BY id", (facility_id,))
    else:
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


def create_facility(
    facility_id: str,
    name: str,
    city: str,
    country: str,
    facility_type: str,
    total_area_sqm: int = 50000,
    director: str = "Facility Director",
    description: str = "",
) -> Dict[str, Any]:
    """Inserts a new facility and auto-provisions its primary plant in SQLite."""
    init_sqlite_db()
    conn = get_sqlite_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO facilities (id, name, city, country, facility_type, total_area_sqm, director, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (facility_id, name, city, country, facility_type, total_area_sqm, director, description))

    # Auto-provision primary plant for the facility
    plant_id = f"{facility_id}_PLANT_1"
    cursor.execute("""
        INSERT OR REPLACE INTO factories (id, facility_id, name, location, country, facility_type, floor_area_sqm, shifts_per_day, plant_manager, operational_status, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (plant_id, facility_id, f"{name} (Primary Line)", city, country, facility_type, total_area_sqm, 3, director, "ACTIVE", f"Primary unit of {name}"))

    # Also provision a starter blueprint layout for this plant
    starter_nodes = [
        {"id": f"{facility_id}_IN", "name": f"{name} Raw Infeed", "type": "Inventory", "bay": "Zone 1 • Infeed", "x": 60, "y": 140, "w": 190, "h": 96, "status": "HEALTHY", "spec": "Certified Material Supply"},
        {"id": f"{facility_id}_M1", "name": "Primary Synthesis Unit", "type": "Machine", "bay": "Zone 2 • Core Processing", "x": 340, "y": 140, "w": 190, "h": 100, "machine_id": f"{facility_id}_M1", "status": "HEALTHY", "spec": "Automated High-Throughput Cell"},
        {"id": f"{facility_id}_QC", "name": "Unit Quality Metrology Bay", "type": "UnitFacility", "bay": "Zone 3 • Unit Inspection", "x": 620, "y": 140, "w": 210, "h": 100, "status": "HEALTHY", "spec": "Integrated Precision QA"},
        {"id": f"{facility_id}_OUT", "name": "Outbound Logistics Bay", "type": "Dispatch", "bay": "Zone 4 • Dispatch", "x": 920, "y": 140, "w": 190, "h": 96, "status": "HEALTHY", "spec": "Automated Dispatch Buffer"}
    ]
    starter_edges = [
        {"from": f"{facility_id}_IN", "to": f"{facility_id}_M1", "path": "M 250 190 L 340 190", "color": "#06b6d4", "stroke": "2.0"},
        {"from": f"{facility_id}_M1", "to": f"{facility_id}_QC", "path": "M 530 190 L 620 190", "color": "#a855f7", "stroke": "2.2"},
        {"from": f"{facility_id}_QC", "to": f"{facility_id}_OUT", "path": "M 830 190 L 920 190", "color": "#10b981", "stroke": "2.2"}
    ]
    cursor.execute("""
        INSERT OR REPLACE INTO factory_blueprints (factory_id, blueprint_name, layout_type, canvas_config_json, nodes_json, edges_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (plant_id, f"{name} Blueprint", "linear_cell", json.dumps({"panX": 60, "panY": 120, "zoom": 0.85}), json.dumps(starter_nodes), json.dumps(starter_edges)))

    conn.commit()
    conn.close()
    return get_facility_by_id(facility_id)

