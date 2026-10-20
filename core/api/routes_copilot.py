"""core/api/routes_copilot.py - Natural Language to Cypher Graph Copilot endpoint."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from core.copilot.service import ask_copilot

router = APIRouter(tags=["copilot"])


@router.post("/api/copilot")
async def copilot_query(request: Request):
    """Natural Language to Cypher Graph Copilot endpoint."""
    try:
        body = await request.json()
        query = body.get("query", "").strip()
        if not query:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Query cannot be empty"})
        result = ask_copilot(query)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
