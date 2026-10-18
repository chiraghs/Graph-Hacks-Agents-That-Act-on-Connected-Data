# Supply Chain Intelligence Agent 🌐⚡
> **Graph Hacks (WeMakeDevs x FalkorDB)**  
> **Track:** *Agents That Act on Connected Data*  
> **Language / Runtime:** Python 3.14 (tested), 3.12+ compatible  
> **Deployment:** Local Docker or Render with FalkorDB Cloud

---

## 📌 Executive Summary
Global supply chains are non-linear, multi-echelon networks of plants, machines, bills of materials, inventory depots, and customer commitments. When predictive maintenance systems detect machine degradation, traditional ERPs fail because relational databases cannot easily answer the core operational question:

> **"If this machine fails, which parts, products, warehouses, and customers are affected, does forecast demand exceed available stock, and what is the cheapest, fastest fix?"**

The **Supply Chain Intelligence Agent** connects predictive maintenance telemetry and demand forecasts with an active **FalkorDB knowledge graph**. The graph does the heavy analytical reasoning—multi-hop traversals, redundancy analysis, supply bottleneck detection, and shortest dependency path discovery—allowing an autonomous AI agent to make auditable, grounded decisions recorded directly back into the graph.

---

## ☁️ Running on FalkorDB Cloud & Local Docker

The project natively supports **FalkorDB Cloud** instances while preserving seamless fallback to local Docker, controlled via environment variables.

### 1. Environment Configuration (`.env`)
Copy [`.env.example`](file:///Volumes/DiskD/HACKATHONS/Agent-SupplyChain/.env.example) to `.env`:
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
Fully idempotent: resets the target graph and seeds ~3 plants, 25 machines, 60 parts, 20 products, 15 suppliers, 6 warehouses, and 40 enterprise customers using Cypher `UNWIND` batch transactions (slashing network latency over Cloud).

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

## 🚀 One-Click Deployment on Render

This repository includes a [`Dockerfile`](file:///Volumes/DiskD/HACKATHONS/Agent-SupplyChain/Dockerfile) (built on `python:3.14-slim`) and a [`render.yaml`](file:///Volumes/DiskD/HACKATHONS/Agent-SupplyChain/render.yaml) Blueprint for instant deployment.

### Exact Deployment Steps on Render:
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

## 🎯 Planted Scenarios & Autonomous Verification

1. **HARMFUL (Action Scheduled)**:  
   Machine **M7** has a critical failure risk of **94%** (predictive failure in 5 days due to sensor drift). Graph traversal proves M7 is the **sole producer** of 3 critical components for Product **P4**. Product P4 has a 30-day forecast demand of 1,200 units but only 400 units in warehouse stock (**800-unit shortfall**). The only alternate supplier has a 12-day lead time (exceeding the 5-day failure window). The agent executes `schedule_action`, committing a `(:Decision)` node connected via `[:BASED_ON]` edges to all supporting graph evidence.
2. **HARMLESS (Explicitly Cleared)**:  
   Machine **M12** also exhibits high failure risk (**88%**, failure in 4 days). However, multi-hop traversal reveals that its parts have **redundant backup machines (M13)** and Product **P12** holds **2,400 units of buffer stock** against a 520-unit forecast. The agent **explicitly clears M12** and takes no disruptive action, avoiding unnecessary operational expense.
3. **Single Point of Failure (SPOF)**:  
   `PART_SPOF_ALLOY` is flagged as having only 1 global supplier (`SUPPLIER_SOLO_SPOF` in East Asia) and 0 internal manufacturing lines.
4. **Benign Noise**:  
   23 remaining machines operate with healthy baselines (low failure risk 4–22%, predicted lifespans 70–140 days).

---

## 🏗️ Graph Model Topology

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
```

### Node & Relationship Schema
- `(:Plant {id, name, location})`
- `(:Machine {id, name, failure_risk, predicted_failure_days})`
- `(:Part {id, name, cost})`
- `(:Product {id, name, forecast_30d, safety_stock})`
- `(:Supplier {id, name, rating})`
- `(:Warehouse {id, name, location, capacity})`
- `(:Customer {id, name, tier})`
- `(:Region {id, name})`
- `(:Decision {id, type, target, reason, ts})` with polymorphic `[:BASED_ON]` relationships to evidence nodes.

---

## 🛠️ The 7 Cypher-Backed MCP Tools

Implemented in [`mcp_server.py`](file:///Volumes/DiskD/HACKATHONS/Agent-SupplyChain/mcp_server.py):

1. **`at_risk_machines(threshold=0.70)`**: Scans for machines where `m.failure_risk >= threshold`.
2. **`downstream_impact(machine_id)`**: 5-hop variable-length traversal: `Machine ➔ Part ➔ Product ➔ Warehouse ➔ Customer`, checking for redundant producers.
3. **`shortfall_check(product_id)`**: Computes numeric inventory gap: `max(0, forecast_30d - total_warehouse_stock)`.
4. **`single_points_of_failure()`**: Global topological scan for components with `<= 1` supplier or `<= 1` producer.
5. **`alternate_sources(part_id)`**: Traverses substitute suppliers connected via `[:ALTERNATE_FOR]` ranked by delivery lead time.
6. **`shortest_path(a_id, b_id)`**: Fast variable-length path traversal explaining dependency chains between disparate entities.
7. **`schedule_action(type, target_id, reason, evidence_ids)`**: **The only write tool**. Commits a `(:Decision)` node with `[:BASED_ON]` edges to every supporting evidence node.

*See [`queries.md`](file:///Volumes/DiskD/HACKATHONS/Agent-SupplyChain/queries.md) for full Cypher query explanations and relational multi-join comparisons.*

---

## 🧠 Heuristic ML (Intentionally Simple)
Per hackathon specifications, complex ML models are intentionally omitted in favor of deterministic heuristics in [`scoring.py`](file:///Volumes/DiskD/HACKATHONS/Agent-SupplyChain/scoring.py):
- **Machine Failure Risk**: Computed via composite z-scores from recent sensor drift (vibration and temperature) versus calibrated baselines, mapped through a sigmoid transfer function:
  $$\text{Composite } z = 0.6 \cdot z_{\text{vibration}} + 0.4 \cdot z_{\text{temperature}}$$
- **Demand Forecasting**: 30-day forward projection calculated using **Single Exponential Smoothing** ($\alpha = 0.35$) over synthetic monthly sales history.

---

## 🖥️ Local Quickstart

### 1. (Optional) Start Local FalkorDB
```bash
docker-compose up -d
```
Runs engine on port `6379` and browser on `http://localhost:3000`.

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
Open **[http://localhost:8000](http://localhost:8000)** in your browser for the full interactive TwinForge control tower.

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
├── seed.py                # High-speed idempotent UNWIND batch graph generator
├── mcp_server.py          # 7 Cypher-backed MCP tools with evidence traceability
├── agent.py               # Autonomous graph reasoning loop with per-tool latency tracking
├── app.py                 # FastAPI backend with /health, SSE streaming & subgraph endpoints
├── static/
│   └── index.html         # Enterprise Control Tower UI (TwinForge theme)
├── queries.md             # Cypher query catalog & SQL multi-join comparison
└── README.md              # Project overview, architecture, and verification
```

---

## 🤖 AI Coding Assistant Disclosure
In accordance with hackathon rules, this project was developed with assistance from **Google Antigravity** (powered by Gemini models) for rapid architecture prototyping, Cypher query optimization on FalkorDB, and dashboard front-end styling.
