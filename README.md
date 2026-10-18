# Supply Chain Intelligence Agent 🌐⚡
> **Graph Hacks (WeMakeDevs x FalkorDB)**  
> **Track:** *Agents That Act on Connected Data*  
> **Language / Runtime:** Python 3.14 (tested), 3.12+ compatible

---

## 📌 Executive Summary
Global supply chains are non-linear, multi-echelon networks of plants, machines, bills of materials, inventory depots, and customer commitments. When predictive maintenance systems detect machine degradation, traditional ERPs fail because relational databases cannot easily answer the core operational question:

> **"If this machine fails, which parts, products, warehouses, and customers are affected, does forecast demand exceed available stock, and what is the cheapest, fastest fix?"**

The **Supply Chain Intelligence Agent** connects predictive maintenance telemetry and demand forecasts with an active **FalkorDB knowledge graph**. The graph does the heavy analytical reasoning—multi-hop traversals, redundancy analysis, supply bottleneck detection, and shortest dependency path discovery—allowing an autonomous AI agent to make auditable, grounded decisions recorded directly back into the graph.

---

## 🎯 Planted Scenarios & Autonomous Verification
The system operates on deterministic synthetic data generated in `seed.py` (seed=42) containing ~3 plants, 25 machines, 60 parts, 20 products, 15 suppliers, 6 warehouses, and 40 enterprise customers:

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

Implemented in [`mcp_server.py`](file:///Volumes/DiskD/HACKATHONS/Agent-SupplyChain/mcp_server.py) following Model Context Protocol principles:

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

## 🚀 Quickstart & Setup

### Prerequisites
- Docker / Docker Compose
- Python 3.14 (or Python 3.12+)

### 1. Start FalkorDB
```bash
docker-compose up -d
```
- FalkorDB engine runs on port `6379`.
- FalkorDB interactive browser UI is accessible at `http://localhost:3000`.

### 2. Set Up Virtual Environment & Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Populate Synthetic Graph Data
```bash
python seed.py
```
Outputs node and relationship verification counts directly from FalkorDB.

### 4. Run the Agent in the Terminal
```bash
python agent.py
```
Traces live tool executions, demonstrates multi-hop reasoning, schedules action for M7, and explicitly clears M12.

### 5. Launch the Web Control Tower Dashboard
```bash
python app.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser:
- **Run Investigation**: Triggers real-time agent execution with live Server-Sent Events (SSE).
- **Tool-Call Trace Panel**: Inspects parameters and outputs of every MCP graph query.
- **Evidence Subgraph Visualizer**: Interactive network canvas (Vis.js) showing the Decision node and its `[:BASED_ON]` graph evidence.
- **Executive Audit Briefing**: Plain-language summaries of actions scheduled vs cleared.

---

## 📦 Repository Structure
```text
.
├── docker-compose.yml     # FalkorDB engine (port 6379) + Web UI (port 3000)
├── requirements.txt       # Pinned dependencies (falkordb, mcp, anthropic, fastapi, uvicorn)
├── scoring.py             # Sensor z-score drift & exponential smoothing demand forecast
├── seed.py                # Deterministic synthetic data generator (seed 42)
├── mcp_server.py          # 7 Cypher-backed MCP tools with evidence traceability
├── agent.py               # Autonomous graph reasoning loop & Anthropic tool-use runner
├── app.py                 # FastAPI server with SSE streaming & subgraph endpoints
├── static/
│   └── index.html         # Enterprise Control Tower UI (Twin-inspired dark theme)
├── queries.md             # Cypher query catalog & SQL multi-join comparison
└── README.md              # Project overview, architecture, and verification
```

---

## 🤖 AI Coding Assistant Disclosure
In accordance with hackathon rules, this project was developed with assistance from **Google Antigravity** (powered by Gemini models) for rapid architecture prototyping, Cypher query optimization on FalkorDB, and dashboard front-end styling.
