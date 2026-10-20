"""core/api/routes_factories.py - SQLite Facilities & Factory Blueprint API.

Provides:
- GET /api/facilities: Lists all manufacturing facilities (Apex Powertrain Network, London Semiconductor Foundry) with nested plants.
- GET /api/facilities/{facility_id}: Returns facility profile and plants.
- GET /api/factories: Lists manufacturing plants (optionally filtered by ?facility_id=...).
- GET /api/factories/{factory_id}: Returns plant profile, blocks/zones, and specifications.
- GET /api/factories/{factory_id}/blueprint: Returns distinct visual blueprint topology (nodes, SVG paths, coordinates).
"""

import re
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from core.db_sqlite import (
    get_all_facilities,
    get_facility_by_id,
    get_all_factories,
    get_factory_by_id,
    get_factory_blueprint,
    create_facility,
)
from core.db import get_graph

router = APIRouter(tags=["factories"])


class FacilityCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str
    city: str = "Detroit"
    country: str = "United States"
    facility_type: str = "Manufacturing & Assembly"
    total_area_sqm: int = 50000
    director: str = "Facility Director"
    description: str = ""


@router.post("/api/facilities")
async def create_new_facility(req: FacilityCreateRequest):
    """Registers a new enterprise facility and provisions its primary plant and starter blueprint."""
    facility_id = req.id
    if not facility_id or not facility_id.strip():
        # Derive an ID from the name
        clean_name = re.sub(r'[^A-Z0-9]+', '_', req.name.upper()).strip('_')
        facility_id = f"FACILITY_{clean_name}" if not clean_name.startswith("FACILITY_") else clean_name

    try:
        facility = create_facility(
            facility_id=facility_id,
            name=req.name,
            city=req.city,
            country=req.country,
            facility_type=req.facility_type,
            total_area_sqm=req.total_area_sqm,
            director=req.director,
            description=req.description,
        )
        return {"status": "success", "message": f"Facility '{req.name}' created successfully", "facility": facility}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create facility: {str(e)}")


@router.get("/api/facilities")
async def list_facilities():
    """Returns all top-level facilities (units) with their constituent manufacturing plants."""
    try:
        facilities = get_all_facilities()
        return {"status": "success", "facilities": facilities}
    except Exception as e:
        return {"status": "error", "message": str(e), "facilities": []}


@router.get("/api/facilities/{facility_id}")
async def get_facility(facility_id: str):
    """Returns details for a specific top-level facility and its plants."""
    facility = get_facility_by_id(facility_id)
    if not facility:
        raise HTTPException(status_code=404, detail=f"Facility '{facility_id}' not found.")
    return {"status": "success", "facility": facility}


@router.get("/api/factories")
async def list_factories(facility_id: Optional[str] = Query(None)):
    """Returns manufacturing plants, optionally filtered by facility_id."""
    try:
        factories = get_all_factories(facility_id=facility_id)
        return {"status": "success", "factories": factories}
    except Exception as e:
        return {"status": "error", "message": str(e), "factories": []}


@router.get("/api/factories/{factory_id}")
async def get_factory(factory_id: str):
    """Returns factory profile, architectural blocks, and specifications from SQLite."""
    factory = get_factory_by_id(factory_id)
    if not factory:
        raise HTTPException(status_code=404, detail=f"Factory '{factory_id}' not found.")
    return {"status": "success", "factory": factory}


@router.get("/api/factories/{factory_id}/blueprint")
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
                if risk >= 0.85:
                    node["status"] = "CRITICAL"
                elif risk >= 0.50:
                    node["status"] = "WARNING"
                else:
                    node["status"] = "HEALTHY"
    except Exception as e:
        # Graceful fallback: serve blueprint even if live graph is offline
        pass

    return {"status": "success", "blueprint": bp}
