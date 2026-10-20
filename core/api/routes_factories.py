"""core/api/routes_factories.py - SQLite Factory Blueprint & Architectural Layout API.

Provides:
- GET /api/factories: Lists all manufacturing facilities with blueprint metadata + live FalkorDB telemetry summary.
- GET /api/factories/{factory_id}: Returns facility profile, blocks/zones, and specifications.
- GET /api/factories/{factory_id}/blueprint: Returns distinct visual blueprint topology (nodes, SVG paths, coordinates).
"""

from fastapi import APIRouter, HTTPException
from core.db_sqlite import get_all_factories, get_factory_by_id, get_factory_blueprint
from core.db import get_graph

router = APIRouter(prefix="/api/factories", tags=["factories"])


@router.get("")
async def list_factories():
    """Returns all manufacturing facilities from SQLite blueprint database."""
    try:
        factories = get_all_factories()
        return {"status": "success", "factories": factories}
    except Exception as e:
        return {"status": "error", "message": str(e), "factories": []}


@router.get("/{factory_id}")
async def get_factory(factory_id: str):
    """Returns factory profile, architectural blocks, and specifications from SQLite."""
    factory = get_factory_by_id(factory_id)
    if not factory:
        raise HTTPException(status_code=404, detail=f"Factory '{factory_id}' not found.")
    return {"status": "success", "factory": factory}


@router.get("/{factory_id}/blueprint")
async def get_blueprint(factory_id: str):
    """Returns distinct visual CAD blueprint topology (nodes, coordinates, SVG edges).
    Dynamically binds live FalkorDB machine telemetry to matching machine nodes in the blueprint.
    """
    bp = get_factory_blueprint(factory_id)
    if not bp:
        raise HTTPException(status_code=404, detail=f"Blueprint for '{factory_id}' not found.")

    # Optionally bind live telemetry from FalkorDB if machines are present
    try:
        g = get_graph()
        telemetry_rows = g.query("""
        MATCH (m:Machine)
        RETURN m.id AS id, m.failure_risk AS risk, m.predicted_failure_days AS days, m.name AS name
        """).result_set or []
        telemetry_map = {r[0]: {"failure_risk": r[1], "predicted_failure_days": r[2], "graph_name": r[3]} for r in telemetry_rows}

        # Merge live telemetry into blueprint machine nodes
        for node in bp.get("nodes", []):
            m_id = node.get("machine_id") or node.get("id")
            if m_id in telemetry_map:
                t = telemetry_map[m_id]
                risk = t["failure_risk"]
                node["failure_risk"] = risk
                node["predicted_failure_days"] = t["predicted_failure_days"]
                node["health_score"] = int(round((1.0 - risk) * 100))
                node["vibration"] = round(1.20 + (risk * 0.65), 2)
                node["temperature"] = round(65.0 + (risk * 9.5), 1)
                node["status"] = "CRITICAL" if risk >= 0.85 else ("WARNING" if risk >= 0.50 else "HEALTHY")
    except Exception as te:
        print(f"[Blueprint Warning] Could not bind FalkorDB telemetry: {te}")

    return {"status": "success", "blueprint": bp}
