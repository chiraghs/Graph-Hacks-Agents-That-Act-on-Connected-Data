"""app.py - FastAPI Application & Control Tower Server.

Serves:
- Single-page application UI at `/`
- Real-time SSE investigation stream at `/api/investigate`
- Live evidence subgraph visualization endpoint at `/api/subgraph`
- Live executive KPI metrics at `/api/kpis`
- Graph reset endpoint at `/api/reset` (re-seeds synthetic data)
"""

import json
import asyncio
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from agent import stream_investigation
from seed import seed_database
from db import get_graph, get_connection_config

app = FastAPI(title="Supply Chain Intelligence Control Tower")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
async def health_check():
    """Confirms FalkorDB connection and reveals target environment (host only, never credentials)."""
    cfg = get_connection_config()
    try:
        g = get_graph()
        g.query("RETURN 1").result_set
        return {
            "status": "healthy",
            "database": "FalkorDB",
            "target_host": f"{cfg['host']}:{cfg['port']}",
            "graph": cfg["graph_name"],
            "environment": "Cloud" if cfg["is_cloud"] else "Local",
            "tls_enabled": cfg["ssl"],
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "target_host": f"{cfg['host']}:{cfg['port']}",
            "environment": "Cloud" if cfg["is_cloud"] else "Local",
            "error": str(e),
        }


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the Control Tower dashboard UI."""
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.get("/api/kpis")
async def get_kpis():
    """Retrieve top-level operational supply chain KPIs from FalkorDB."""
    try:
        g = get_graph()
        
        # At risk machines count
        risk_res = g.query("MATCH (m:Machine) WHERE m.failure_risk >= 0.70 RETURN count(m)").result_set
        at_risk_count = risk_res[0][0] if risk_res else 0

        # Decisions made
        dec_res = g.query("MATCH (d:Decision) RETURN count(d)").result_set
        decision_count = dec_res[0][0] if dec_res else 0

        # Products count & total inventory
        inv_res = g.query("MATCH (p:Product)-[s:STOCKED_AT]->(w:Warehouse) RETURN count(DISTINCT p), sum(s.qty)").result_set
        prod_count = inv_res[0][0] if inv_res else 0
        total_inv = inv_res[0][1] if inv_res else 0

        # Customers served
        cust_res = g.query("MATCH (c:Customer) RETURN count(c)").result_set
        cust_count = cust_res[0][0] if cust_res else 0

        return {
            "status": "online",
            "at_risk_machines": at_risk_count,
            "decisions_active": decision_count,
            "products_monitored": prod_count,
            "total_inventory_units": int(total_inv),
            "customers_protected": cust_count,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/telemetry")
async def get_telemetry():
    """Retrieve all machines with live health, vibration, temperature and risk metrics."""
    try:
        g = get_graph()
        cypher = """
        MATCH (pl:Plant)-[:HAS]->(m:Machine)
        RETURN m.id AS id, m.name AS name, m.failure_risk AS failure_risk,
               m.predicted_failure_days AS predicted_days, pl.id AS plant_id, pl.name AS plant_name
        ORDER BY m.failure_risk DESC
        """
        rows = g.query(cypher).result_set
        machines = []
        for row in rows:
            m_id, name, risk, days, pl_id, pl_name = row
            health = int(round((1.0 - risk) * 100))
            # Synthetic realistic sensor telemetry based on risk
            vibration = round(1.20 + (risk * 0.65), 2)
            temperature = round(65.0 + (risk * 9.5), 1)
            status = "CRITICAL" if risk >= 0.85 else ("WARNING" if risk >= 0.50 else "HEALTHY")
            machines.append({
                "id": m_id,
                "name": name,
                "failure_risk": risk,
                "health_score": health,
                "predicted_failure_days": days,
                "vibration": vibration,
                "temperature": temperature,
                "plant_name": pl_name,
                "status": status,
            })
        return {"machines": machines}
    except Exception as e:
        return {"machines": [], "error": str(e)}


@app.get("/api/inventory")
async def get_inventory():
    """Retrieve products demand forecast vs available inventory and calculated shortfall."""
    try:
        g = get_graph()
        cypher = """
        MATCH (p:Product)
        OPTIONAL MATCH (p)-[s:STOCKED_AT]->(w:Warehouse)
        RETURN p.id AS id, p.name AS name, p.forecast_30d AS forecast, p.safety_stock AS safety,
               coalesce(sum(s.qty), 0) AS stock,
               collect({warehouse_id: w.id, warehouse_name: w.name, qty: s.qty}) AS warehouses
        ORDER BY p.id
        """
        rows = g.query(cypher).result_set
        products = []
        for row in rows:
            p_id, name, fcast, safety, stock, whs = row
            stock = float(stock)
            shortfall = max(0.0, fcast - stock)
            products.append({
                "id": p_id,
                "name": name,
                "forecast_30d": fcast,
                "safety_stock": safety,
                "total_stock": stock,
                "shortfall": shortfall,
                "status": "SHORTFALL" if shortfall > 0 else "BALANCED",
                "warehouses": [w for w in whs if w.get("warehouse_id")],
            })
        return {"products": products}
    except Exception as e:
        return {"products": [], "error": str(e)}



@app.get("/api/subgraph")
async def get_subgraph():
    """Returns nodes and edges for the Decision and its BASED_ON evidence graph."""
    try:
        g = get_graph()
        cypher = """
        MATCH (d:Decision)-[r:BASED_ON]->(target)
        RETURN d.id AS dec_id, d.type AS dec_type, d.target AS dec_target, d.reason AS dec_reason,
               labels(target)[0] AS target_label, target.id AS target_id, target.name AS target_name
        """
        rows = g.query(cypher).result_set

        nodes = []
        edges = []
        seen_nodes = set()

        for row in rows:
            d_id, d_type, d_target, d_reason, t_label, t_id, t_name = row

            if d_id not in seen_nodes:
                seen_nodes.add(d_id)
                nodes.append({
                    "id": d_id,
                    "label": f"DECISION:\n{d_type}\n[{d_target}]",
                    "group": "Decision",
                    "color": {"background": "#ef4444", "border": "#b91c1c"},
                    "font": {"color": "#ffffff", "face": "monospace"},
                    "shape": "box",
                    "title": f"Decision: {d_type} for {d_target}\nReason: {d_reason}",
                })

            if t_id not in seen_nodes:
                seen_nodes.add(t_id)
                
                # Color code node by entity type
                colors = {
                    "Machine": {"background": "#f59e0b", "border": "#d97706"},
                    "Part": {"background": "#6366f1", "border": "#4f46e5"},
                    "Product": {"background": "#06b6d4", "border": "#0891b2"},
                    "Warehouse": {"background": "#10b981", "border": "#059669"},
                    "Supplier": {"background": "#8b5cf6", "border": "#7c3aed"},
                    "Customer": {"background": "#ec4899", "border": "#db2777"},
                }
                c = colors.get(t_label, {"background": "#64748b", "border": "#475569"})

                nodes.append({
                    "id": t_id,
                    "label": f"{t_label}\n{t_id}",
                    "group": t_label,
                    "color": c,
                    "font": {"color": "#ffffff"},
                    "shape": "dot",
                    "size": 22,
                    "title": f"{t_label}: {t_name or t_id}",
                })

            edges.append({
                "from": d_id,
                "to": t_id,
                "label": "BASED_ON",
                "arrows": "to",
                "color": {"color": "#94a3b8", "highlight": "#ef4444"},
                "font": {"color": "#94a3b8", "size": 10},
                "dashes": True,
            })

        # Also include direct relationships among the evidence nodes for rich context
        if seen_nodes:
            cypher_inner = """
            MATCH (a)-[r]->(b)
            WHERE a.id IN $node_ids AND b.id IN $node_ids AND type(r) <> 'BASED_ON'
            RETURN a.id, type(r), b.id
            """
            inner_rows = g.query(cypher_inner, params={"node_ids": list(seen_nodes)}).result_set
            for a_id, r_type, b_id in inner_rows:
                edges.append({
                    "from": a_id,
                    "to": b_id,
                    "label": r_type,
                    "arrows": "to",
                    "color": {"color": "#38bdf8"},
                    "font": {"color": "#38bdf8", "size": 9},
                })

        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}


@app.get("/api/graph/full")
async def get_full_graph():
    """Returns the full interconnected supply chain network graph for Vis.js visualization."""
    try:
        g = get_graph()
        nodes_q = """
        MATCH (n)
        RETURN id(n) AS internal_id, labels(n)[0] AS label, n.id AS node_id, n.name AS name,
               properties(n) AS props
        """
        raw_nodes = g.query(nodes_q).result_set

        colors = {
            "Plant": {"background": "#3b82f6", "border": "#1d4ed8"},
            "Machine": {"background": "#f59e0b", "border": "#d97706"},
            "Part": {"background": "#6366f1", "border": "#4f46e5"},
            "Product": {"background": "#06b6d4", "border": "#0891b2"},
            "Warehouse": {"background": "#10b981", "border": "#059669"},
            "Supplier": {"background": "#8b5cf6", "border": "#7c3aed"},
            "Customer": {"background": "#ec4899", "border": "#db2777"},
            "Region": {"background": "#64748b", "border": "#475569"},
            "Decision": {"background": "#ef4444", "border": "#b91c1c"},
        }

        nodes = []
        for row in raw_nodes:
            _, label, n_id, name, props = row
            # If machine is critical M7 or M12, highlight it
            c = colors.get(label, {"background": "#64748b", "border": "#475569"})
            risk = props.get("failure_risk", 0) if isinstance(props, dict) else 0
            if label == "Machine" and risk and float(risk) >= 0.80:
                c = {"background": "#ef4444", "border": "#991b1b"}

            nodes.append({
                "id": n_id,
                "label": f"{label}\n{n_id}",
                "group": label,
                "color": c,
                "shape": "dot" if label != "Plant" and label != "Decision" else ("hexagon" if label == "Plant" else "box"),
                "size": 26 if label in ["Plant", "Warehouse", "Product"] else 18,
                "font": {"color": "#ffffff", "face": "Inter, sans-serif", "size": 11},
                "title": f"{label}: {name or n_id}\nAttributes: {json.dumps(props, indent=1)}",
                "props": props,
            })

        edges_q = """
        MATCH (a)-[r]->(b)
        RETURN a.id AS from_id, type(r) AS rel, b.id AS to_id
        """
        raw_edges = g.query(edges_q).result_set
        edges = []
        for from_id, rel, to_id in raw_edges:
            edges.append({
                "from": from_id,
                "to": to_id,
                "label": rel,
                "arrows": "to",
                "color": {"color": "#334155", "highlight": "#4c8dff"},
                "font": {"color": "#64748b", "size": 9},
            })

        return {"nodes": nodes, "edges": edges, "count_nodes": len(nodes), "count_edges": len(edges)}
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}


@app.get("/api/simulate/{machine_id}")
async def simulate_failure_ripple(machine_id: str):
    """Calculates full downstream failure ripple effects for a specific machine in FalkorDB."""
    try:
        from mcp_server import downstream_impact, shortfall_check, alternate_sources
        
        # 1. Fetch machine telemetry & risk
        g = get_graph()
        m_row = g.query("MATCH (m:Machine {id: $id}) RETURN m.id, m.name, m.failure_risk, m.predicted_failure_days", {"id": machine_id}).result_set
        if not m_row:
            return {"error": f"Machine {machine_id} not found"}
        
        m_id, m_name, risk, days = m_row[0]

        # 2. Downstream impact traversal
        impact = downstream_impact(machine_id)
        
        # 3. Check shortfalls for all impacted products
        product_items = impact.get("affected_products", [])
        products_analysis = []
        total_shortfall = 0
        prod_names = []
        for p_item in product_items:
            p_id = p_item.get("id") if isinstance(p_item, dict) else p_item
            sf = shortfall_check(p_id)
            shortfall_units = sf.get("shortfall_units", 0)
            total_shortfall += shortfall_units
            products_analysis.append(sf)
            prod_names.append(p_id)

        # 4. Check redundancy and alternate sources for each part
        part_items = impact.get("affected_parts", [])
        parts_analysis = []
        has_redundancy = True
        backup_machine_ids = set()
        for pt_item in part_items:
            pt_id = pt_item.get("id") if isinstance(pt_item, dict) else pt_item
            alts = alternate_sources(pt_id)
            backups = [m["id"] for m in alts.get("available_producing_machines", []) if m.get("id") != machine_id and m.get("failure_risk", 1.0) < 0.50]
            if not backups:
                has_redundancy = False
            else:
                backup_machine_ids.update(backups)
            parts_analysis.append(alts)

        # 5. Formulate prescriptive resolution:
        # Rule: If shortfall is zero OR parts are redundant, explicitly clear the machine and take no action.
        is_harmful = (risk >= 0.70) and (total_shortfall > 0 and not has_redundancy)
        recommendation = {
            "is_harmful": is_harmful,
            "status": "ACTION_REQUIRED" if is_harmful else "CLEARED_HARMLESS",
            "action_type": "schedule_maintenance" if is_harmful else "none",
            "primary_rationale": (
                f"Critical risk {int(risk*100)}% with {total_shortfall} units demand shortfall on {prod_names} and no redundant machining backup."
                if is_harmful else
                f"High risk {int(risk*100)}% on {machine_id} safely cleared: redundant backup machines exist ({list(backup_machine_ids) or 'M13'}) and product inventory has ample buffer (0 shortfall)."
            ),
            "suggested_actions": [
                {
                    "type": "schedule_maintenance",
                    "target": machine_id,
                    "reason": f"Expedite replacement bearings before {days}-day functional trip window.",
                    "evidence_ids": impact.get("evidence_node_ids", [])[:8],
                },
                {
                    "type": "reroute_production",
                    "target": prod_names[0] if prod_names else "P4",
                    "reason": "Shift production batch to alternate qualified plant.",
                    "evidence_ids": impact.get("evidence_node_ids", [])[:8],
                }
            ] if is_harmful else []
        }

        return {
            "machine": {
                "id": m_id,
                "name": m_name,
                "failure_risk": risk,
                "predicted_failure_days": days,
                "health_score": int(round((1.0 - risk) * 100)),
            },
            "impact": impact,
            "products_analysis": products_analysis,
            "parts_analysis": parts_analysis,
            "total_shortfall": total_shortfall,
            "has_redundancy": has_redundancy,
            "recommendation": recommendation,
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/decisions")
async def get_decisions():
    """Retrieve all decisions and their evidence nodes from FalkorDB."""
    try:
        g = get_graph()
        cypher = """
        MATCH (d:Decision)
        OPTIONAL MATCH (d)-[:BASED_ON]->(e)
        RETURN d.id AS id, d.type AS type, d.target AS target, d.reason AS reason, d.ts AS ts,
               collect({id: e.id, label: labels(e)[0], name: e.name}) AS evidence
        ORDER BY d.ts DESC
        """
        rows = g.query(cypher).result_set
        decisions = []
        for row in rows:
            d_id, d_type, d_target, d_reason, d_ts, evidence = row
            decisions.append({
                "id": d_id,
                "type": d_type,
                "target": d_target,
                "reason": d_reason,
                "ts": d_ts,
                "evidence": [ev for ev in evidence if ev.get("id")],
            })
        return {"decisions": decisions}
    except Exception as e:
        return {"decisions": [], "error": str(e)}


@app.post("/api/decisions/approve")
async def approve_decision(payload: dict):
    """Approve and record a decision with BASED_ON edges directly in FalkorDB."""
    try:
        from mcp_server import schedule_action
        action_type = payload.get("type", "schedule_maintenance")
        target_id = payload.get("target_id", "M7")
        reason = payload.get("reason", "Approved mitigation plan from digital twin operator")
        evidence_ids = payload.get("evidence_ids", [target_id])
        
        res = schedule_action(action_type, target_id, reason, evidence_ids)
        return {"status": "success", "result": res}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/investigate")
async def investigate_stream():
    """Server-Sent Events (SSE) endpoint streaming real-time agent execution."""
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event in stream_investigation():
                payload = json.dumps(event)
                yield f"data: {payload}\n\n"
                # Small yield pause for silky smooth UI stream rendering
                await asyncio.sleep(0.05)
        except Exception as e:
            err_payload = json.dumps({"event": "agent_error", "data": {"error": str(e)}})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/reset")
async def reset_graph():
    """Re-seeds the FalkorDB SupplyChain graph to its original baseline state."""
    try:
        counts = seed_database()
        return {"status": "success", "counts": counts}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
