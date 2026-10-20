"""core/api/routes_decisions.py - Prescriptive decision approval & graph reset endpoints."""

from fastapi import APIRouter
from core.db import get_graph
from core.mcp.server import schedule_action
from core.graph.seed import seed_database

router = APIRouter(tags=["decisions"])


@router.get("/api/decisions")
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


@router.post("/api/decisions/approve")
async def approve_decision(payload: dict):
    """Approve and record a decision with BASED_ON edges directly in FalkorDB."""
    try:
        raw_type = payload.get("type") or payload.get("decision_type") or "schedule_maintenance"
        if raw_type in {"schedule_maintenance", "reroute_production", "expedite_order"}:
            action_type = raw_type
        elif "reroute" in raw_type.lower():
            action_type = "reroute_production"
        else:
            action_type = "schedule_maintenance"

        target_id = payload.get("target_id") or payload.get("target") or "M7"
        reason = payload.get("reason", "Approved mitigation plan from digital twin operator")
        evidence_ids = payload.get("evidence_ids", [target_id, "PT-4", "P4", "C1"])
        
        res = schedule_action(action_type, target_id, reason, evidence_ids)
        return {"status": "success", "result": res}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/api/reset")
async def reset_graph():
    """Re-seeds the FalkorDB SupplyChain graph to its original baseline state."""
    try:
        counts = seed_database()
        return {"status": "success", "counts": counts}
    except Exception as e:
        return {"status": "error", "message": str(e)}
