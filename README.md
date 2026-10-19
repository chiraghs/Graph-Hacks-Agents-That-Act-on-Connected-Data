# TwinForge Connected Graph 🌐⚡
> **Graph Hacks: Context for AI Agents (WeMakeDevs x FalkorDB)**  
> **Track:** *Track 01 — Agents That Act on Connected Data*  
> **Database:** FalkorDB (Cypher Query Engine, Local Docker & FalkorDB Cloud TLS)  
> **Runtime:** Python 3.14 (tested), 3.12+ compatible  
> **Deployment:** Local Docker or One-Click Cloud on Render  

[![FalkorDB](https://img.shields.io/badge/Database-FalkorDB-red.svg)](https://www.falkordb.com/)
[![MCP](https://img.shields.io/badge/Protocol-Model_Context_Protocol_(MCP)-blue.svg)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![TailwindCSS](https://img.shields.io/badge/UI-TailwindCSS_&_Vis.js-38bdf8.svg)](https://tailwindcss.com/)

---

## 🎥 3-Minute Video Walkthrough

📺 **Direct Video File**: [twinforge_connected_graph_walkthrough_demo.mp4](twinforge_connected_graph_walkthrough_demo.mp4) *(or stream at `http://localhost:8000/static/twinforge_connected_graph_walkthrough_demo.mp4`)*  
🎙️ **Narration**: Studio-grade natural human neural voice (`en-US-ChristopherNeural` via Azure Speech)  

```
00:00 ─── Intro & Architecture Overview (FalkorDB Property Graph)
00:30 ─── Connected-Graph & Multi-Hop Blast Radius Simulation
01:02 ─── Command Center & Real-Time Production KPIs
01:30 ─── Autonomous AI Agent Investigation Console (Live SSE Cypher Loop)
02:00 ─── Multi-Echelon Supply Chain Simulator & Supplier Lead Times
02:27 ─── Human-in-the-Loop Prescriptive Approvals & BASED_ON Lineage
02:53 ─── Cryptographic Audit Trail, Control Room & FalkorDB Integrations
```

---

## 📌 Executive Summary

**TwinForge Connected Graph** is an **autonomous industrial digital twin and self-healing supply chain intelligence platform** built natively on **FalkorDB**.

Global manufacturing networks are non-linear, multi-echelon webs of physical plant machinery, bills of materials (BOM), regional warehouses, and enterprise customer delivery contracts. When predictive maintenance systems detect machine degradation, traditional ERPs fail because relational databases cannot easily answer the core operational question:

> **"If this machine fails, which parts, products, warehouses, and customers are affected, does forecast demand exceed available stock, and what is the cheapest, fastest fix?"**

TwinForge Connected Graph connects predictive maintenance telemetry and demand forecasts directly to an active **FalkorDB knowledge graph**. The graph does the heavy analytical reasoning—multi-hop blast radius traversals, redundancy analysis, supply bottleneck detection, and shortest dependency path discovery—allowing an autonomous AI agent to make auditable, grounded decisions recorded directly back into the graph.

---

## 💥 The Core Problem: Why Relational Databases Fail

In conventional manufacturing and logistics:
* **IoT sensor data** lives in time-series databases.
* **Bills of Materials (BOM)** live in product lifecycle management (PLM) tools.
* **Inventory & orders** live in ERP systems (SAP, Oracle).
* **Customer contracts & SLAs** live in CRM databases.

```
Conventional Relational Approach:
IoT Alert ──> [5 to 7 SQL JOINs across ERP, MES, CRM tables] ──> Slow (Seconds/Timeouts)
                                                                 Fragile nested queries
                                                                 Black-box AI guessing
```

When an alert triggers, tracing how a broken bearing impacts a customer order requires joining 5 to 8 massive relational tables. In large enterprises, these queries are too slow or impossible to run in real time during an agent loop. As a result, companies react **after** production lines stop.

### The FalkorDB Shift: Unified Graph Context

In FalkorDB, all these silos are modeled as a **single, unified property graph**:

```
(Machine: M7)
   │  [:PRODUCES]
   ▼
(Part: PT-4 Rotor) ──[:USED_IN]──> (Product: P4 Turbine)
                                       │  [:STOCKED_AT]
                                       ▼
(Customer: Kestrel Robotics) <──[:SERVES]── (Warehouse: Atlantic Hub)
```

1. **Sub-Millisecond Traversal**: 6 hops take less than **10ms**, enabling the AI agent to execute multiple diagnostic queries in a tight loop.
2. **Zero Hallucination**: The agent's reasoning is grounded in deterministic graph structure.
3. **Auditable Lineage**: Every decision made by the agent links directly to the exact graph nodes that justified it via `[:BASED_ON]` edges.

---

## 🏗️ Knowledge Graph Topology (Live in FalkorDB)

The supply chain graph contains **175 nodes** and **465 relationships**:

| Node Label | Count | Real-World Role | Key Properties |
| :--- | :---: | :--- | :--- |
| **`Plant`** | 5 | Manufacturing facilities (e.g. Leipzig, Austin, Tokyo) | `id`, `name`, `status`, `capacity_utilization` |
| **`Machine`** | 20 | Physical shopfloor assets (Robots, CNCs, Press units) | `id`, `name`, `failure_risk`, `predicted_failure_days` |
| **`Part`** | 30 | Components produced by machines | `id`, `name`, `single_point_of_failure`, `lead_time_days` |
| **`Product`** | 20 | Finished goods assembled from parts | `id`, `name`, `demand_units`, `shortfall_projected` |
| **`Warehouse`** | 10 | Regional distribution and buffering centers | `id`, `name`, `inventory_level`, `capacity` |
| **`Customer`** | 40 | Enterprise buyers with SLA agreements | `id`, `name`, `sla_tier`, `penalty_per_day_late` |
| **`Supplier`** | 15 | Global parts vendors & backup foundries | `id`, `name`, `lead_time_days`, `expedite_cost_multiplier` |
| **`Region`** | 3 | Geographic macro-zones (Americas, EMEA, APAC) | `id`, `name` |
| **`Decision`** | Live | Action records created by the agent | `id`, `type`, `target`, `reason`, `timestamp` |

### Graph Schema

```mermaid
graph TD
    Plant["(:Plant)"] -->|:HAS| Machine["(:Machine)"]
    Machine -->|:PRODUCES| Part["(:Part)"]
    Supplier["(:Supplier)"] -->|:SUPPLIES {lead_time_days}| Part
    Supplier -->|:LOCATED_IN| Region["(:Region)"]
    Supplier <-->|:ALTERNATE_FOR| SupplierAlt["(:Supplier)"]
    Part -->|:USED_IN {qty_per_unit}| Product["(:Product)"]
    Product -->|:STOCKED_AT {qty}| Warehouse["(:Warehouse)"]
    Warehouse -->|:SERVES| Customer["(:Customer)"]
    Decision["(:Decision {id, type, target, reason, ts})"] -.->|:BASED_ON| Machine
    Decision -.->|:BASED_ON| Product
    Decision -.->|:BASED_ON| Part
    Decision -.->|:BASED_ON| Warehouse
    Decision -.->|:BASED_ON| Supplier
    Decision -.->|:BASED_ON| Customer
```

---

## 🛠️ The 7 Cypher-Backed MCP Tools

Implemented in [`mcp_server.py`](mcp_server.py) conforming strictly to the **Model Context Protocol (MCP)**:

```
                      ┌───────────────────────────────┐
                      │    Autonomous AI Agent Loop   │
                      └───────────────┬───────────────┘
                                      │ MCP Tool Protocol
                                      ▼
                      ┌───────────────────────────────┐
                      │    mcp_server.py (7 Tools)    │
                      └───────────────┬───────────────┘
                                      │ Native Cypher
                                      ▼
                      ┌───────────────────────────────┐
                      │      FalkorDB Graph Engine    │
                      │     (Graph: supply_chain)     │
                      └───────────────────────────────┘
```

1. **`at_risk_machines(threshold=0.70)`**: Scans for machines where `m.failure_risk >= threshold`.
2. **`downstream_impact(machine_id)`**: 5-hop variable-length traversal: `Machine ➔ Part ➔ Product ➔ Warehouse ➔ Customer`, checking for redundant producers.
3. **`shortfall_check(product_id)`**: Computes numeric inventory gap: `max(0, forecast_30d - total_warehouse_stock)`.
4. **`single_points_of_failure()`**: Global topological scan for components with `<= 1` supplier or `<= 1` producer.
5. **`alternate_sources(part_id)`**: Traverses substitute suppliers connected via `[:ALTERNATE_FOR]` ranked by delivery lead time.
6. **`shortest_path(a_id, b_id)`**: Fast variable-length path traversal explaining dependency chains between disparate entities.
7. **`schedule_action(type, target_id, reason, evidence_ids)`**: **The only write tool**. Commits a `(:Decision)` node with `[:BASED_ON]` edges to every supporting evidence node.

*See [`queries.md`](queries.md) for full Cypher query explanations and relational multi-join comparisons.*

---

## 🚨 The Autonomous Incident Walkthrough (M7 Crisis Demo)

```
[1. OBSERVE]
Sensor vibration on robotic arm A-ROB-03 (M7) spikes to 6.22 mm/s (Failure risk: 94%, breakdown in 5 days).
                    │
                    ▼
[2. INVESTIGATE (Graph Traversal)]
Agent calls `downstream_impact('M7')`:
• M7 produces Part PT-4 (Precision Rotor).
• PT-4 is a Single Point of Failure (no other machine at Plant 1 can make it).
• PT-4 is used exclusively in Product P4 (Smart Turbine Module).
                    │
                    ▼
[3. PREDICT (Inventory Buffer)]
Agent calls `shortfall_check('P4')`:
• Total warehouse stock: 400 units.
• 30-day forecast demand: 1,200 units.
• Projected Shortfall: 800 units within 23 hours of line stoppage.
                    │
                    ▼
[4. SIMULATE (Alternate Sourcing)]
Agent calls `alternate_sources('PT-4')`:
• Emergency Supplier lead time: 12 days. (Exceeds the 5-day machine failure window!)
• Redundant capacity found at Plant 2 (Leipzig).
                    │
                    ▼
[5. RECOMMEND & APPROVE]
Prescriptive Plan: Reroute P4 production to Leipzig & schedule emergency bearing swap on M7.
                    │
                    ▼
[6. COMMIT TO GRAPH]
Agent calls `schedule_action`:
FalkorDB creates: (:Decision {id: "DEC_...", type: "reroute_production"})
                     -[:BASED_ON]-> (:Machine {id: "M7"})
                     -[:BASED_ON]-> (:Part {id: "PT-4"})
                     -[:BASED_ON]-> (:Product {id: "P4"})
                     -[:BASED_ON]-> (:Customer {id: "ORD-1042"})
```

### Contrast Scenario: Machine M12 (Harmless Anomaly)
Machine **M12** also exhibits high failure risk (**88%**, failure in 4 days). However, multi-hop traversal reveals that its parts have **redundant backup machines (M13)** and Product **P12** holds **2,400 units of buffer stock** against a 520-unit forecast. The agent **explicitly clears M12** and takes no disruptive action, avoiding unnecessary operational expense.

---

## 🏆 Hackathon Alignment: Track 01 (Agents That Act on Connected Data)

| Track 01 Key Focus (From Brief) | How TwinForge Connected Graph Delivers |
| :--- | :--- |
| **Multi-hop reasoning** | **6-Hop Traversal**: `(Machine) → (Part) → (Product) → (Warehouse) → (Customer) → (Region)`. Traverses deep dependencies in <10ms. |
| **Graph queries as agent tools** | **7 Dedicated Cypher Tools**: Health checks, BOM traversal, inventory levels, alternate supplier matching in `mcp_server.py`. |
| **Tool selection through MCP** | **Model Context Protocol (MCP)**: Native Python MCP server conforming strictly to the standard. |
| **Actions based on graph context** | **FalkorDB Write Tool (`schedule_action`)**: Agent writes `:Decision` nodes connected directly to graph evidence. |
| **Explainable results** | **Lineage & Vis.js Subgraph**: The agent renders the mathematical proof graph justifying the mitigation plan. |

---

## ☁️ Running on FalkorDB Cloud & Local Docker

The project natively supports **FalkorDB Cloud** instances while preserving seamless fallback to local Docker, controlled via environment variables.

### 1. Environment Configuration (`.env`)
Copy [`.env.example`](.env.example) to `.env`:
```bash
cp .env.example .env
```

Set the connection variables according to your environment:

| Variable | Local Docker Default | FalkorDB Cloud Example | Description |
| :--- | :--- | :--- | :--- |
| `FALKORDB_HOST` | `localhost` | `cluster-id.falkordb.cloud` | Database server hostname |
| `FALKORDB_PORT` | `6379` | `6379` | Database connection port |
| `FALKORDB_USERNAME` | *(empty)* | `default` | ACL username (if applicable) |
| `FALKORDB_PASSWORD` | *(empty)* | `your_cloud_password` | Database authentication token |
| `FALKORDB_SSL` | `false` | `true` | Enables TLS encryption for Cloud |
| `FALKORDB_GRAPH` | `supply_chain` | `supply_chain` | Active graph name |
| `ANTHROPIC_API_KEY`| *(optional)* | *(optional)* | For Claude tool-use loop (autonomous graph fallback if omitted) |

> [!NOTE]
> **No credentials or secrets are committed to this repository**. All secrets are loaded via `python-dotenv` from `.env`, which is ignored by git. Judges and evaluators can connect the agent to their own FalkorDB Cloud or local Docker database in seconds.

### 2. Verify Database Connectivity
```bash
python check_connection.py
```
Pings the target database, runs a `RETURN 1` sanity test, and outputs connection status without exposing sensitive credentials.

### 3. High-Speed Batched Seeding (`seed.py`)
```bash
python seed.py
```
Fully idempotent: resets the target graph and seeds 175 nodes and 465 edges using Cypher `UNWIND` batch transactions (slashing network latency over Cloud).

### 4. Automated Parity Test Suite (`test_scenarios.py`)
```bash
python test_scenarios.py
```
Runs 5 automated regression and parity checks against Cloud/Local FalkorDB:
- `at_risk_machines` flags M7 (94%) and M12 (88%).
- `shortfall_check` proves Product P4 has an 800-unit deficit.
- M12's downstream impact proves 0 shortfall and redundant backup machines (M13).
- `single_points_of_failure` discovers `PART_SPOF_ALLOY`.
- `schedule_action` creates a `(:Decision)` node linked to evidence via `[:BASED_ON]` and cleanly self-audits.

### 5. Clean Demo Reset
```bash
python reset_decisions.py
```
Deletes all `(:Decision)` nodes from the graph so evaluators can start fresh and demonstrate live autonomous decision commits.

---

## 🖥️ Local Quickstart

### 1. (Optional) Start Local FalkorDB
```bash
docker-compose up -d
```
Runs FalkorDB engine on port `6379` and FalkorDB Browser on `http://localhost:3000`.

### 2. Set Up Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Agent in Terminal
```bash
python agent.py
```
Traces live tool executions, per-tool latency measurements, schedules action for M7, and clears M12.

### 4. Launch Control Tower Dashboard
```bash
python app.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser for the full interactive TwinForge Connected Graph control tower.

---

## 🚀 One-Click Deployment on Render

This repository includes a [`Dockerfile`](Dockerfile) (built on `python:3.14-slim`) and a [`render.yaml`](render.yaml) Blueprint for instant deployment.

1. Log in to [dashboard.render.com](https://dashboard.render.com/).
2. Click **New +** ➔ **Blueprint** (or **Web Service**).
3. Connect your fork or repository: `https://github.com/chiraghs/Graph-Hacks-Agents-That-Act-on-Connected-Data`.
4. Render will detect `render.yaml` and configure the web service:
   - **Runtime**: Docker (`Dockerfile`)
   - **Health Check Path**: `/health`
5. In the **Environment Variables** / **Secret Settings** tab, configure:
   - `FALKORDB_HOST`: your FalkorDB Cloud cluster host
   - `FALKORDB_PORT`: `6379`
   - `FALKORDB_PASSWORD`: your FalkorDB Cloud password
   - `FALKORDB_SSL`: `true`
   - `FALKORDB_GRAPH`: `supply_chain`
   - *(Optional)* `ANTHROPIC_API_KEY`: your Claude API key
6. Click **Apply / Deploy**. The service will build and go live with zero downtime!

---

## 📦 Repository Structure
```text
.
├── Dockerfile             # Production container for Render / Cloud deployment
├── render.yaml            # Render Blueprint one-click deployment spec
├── docker-compose.yml     # Local FalkorDB engine (port 6379) + Web UI (port 3000)
├── requirements.txt       # Pinned dependencies (falkordb, mcp, anthropic, fastapi, uvicorn)
├── .env.example           # Documented configuration template (Cloud & Local)
├── db.py                  # Unified FalkorDB connection helper with TLS & auto-retry
├── check_connection.py    # Diagnostic connectivity test tool
├── test_scenarios.py      # 5/5 automated parity & scenario verification suite
├── reset_decisions.py     # Clean-slate reset utility for live demos
├── scoring.py             # Sensor z-score drift & exponential smoothing demand forecast
├── seed.py                # High-speed idempotent UNWIND batch graph generator (175 nodes, 465 edges)
├── mcp_server.py          # 7 Cypher-backed MCP tools with evidence traceability
├── agent.py               # Autonomous graph reasoning loop with per-tool latency tracking
├── app.py                 # FastAPI backend with /health, SSE streaming & subgraph endpoints
├── static/
│   ├── index.html         # Enterprise Control Tower UI (TwinForge Connected Graph theme)
│   └── twinforge_connected_graph_walkthrough_demo.mp4 # Direct streamable 3.4-min walkthrough video
├── video_build/           # Video synthesis pipeline (edge-tts natural voiceover, Playwright tour)
├── queries.md             # Cypher query catalog & SQL multi-join comparison
└── README.md              # Project overview, architecture, and verification
```

---

## 🤖 AI Coding Assistant Disclosure
In accordance with hackathon rules, this project was developed with assistance from **Google Antigravity** (powered by Gemini models) for rapid architecture prototyping, Cypher query optimization on FalkorDB, and dashboard front-end styling.
