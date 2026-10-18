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
from mcp_server import get_graph

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
