"""app.py - TwinForge Connected Graph FastAPI Entrypoint.

Clean, modular application entrypoint mounting:
- /static: Client assets (HTML, CSS, modular JS)
- Single-page application routes (/twin, /dashboard, /agents, etc.)
- /api: Modular routers (telemetry, simulation, agent, decisions, copilot)
"""

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from core.api import (
    telemetry_router,
    simulation_router,
    agent_router,
    decisions_router,
    copilot_router,
)

app = FastAPI(title="TwinForge Connected Graph — Control Tower & Digital Twin")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount modular API routers
app.include_router(telemetry_router)
app.include_router(simulation_router)
app.include_router(agent_router)
app.include_router(decisions_router)
app.include_router(copilot_router)


# Single Page Application Routes (Catch-all for clean SPA client-side routing)
@app.get("/", response_class=HTMLResponse)
@app.get("/home", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
@app.get("/twin", response_class=HTMLResponse)
@app.get("/connected-graph", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/agents", response_class=HTMLResponse)
@app.get("/control-room", response_class=HTMLResponse)
@app.get("/approvals", response_class=HTMLResponse)
@app.get("/simulator", response_class=HTMLResponse)
@app.get("/audit", response_class=HTMLResponse)
@app.get("/integrations", response_class=HTMLResponse)
async def serve_index():
    """Serves the TwinForge Connected Graph Digital Twin Studio SPA."""
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_spa_catchall(full_path: str):
    """Catch-all router allowing full browser refresh on any client-side route."""
    clean_path = full_path.strip("/")
    if clean_path.startswith("api") or clean_path.startswith("static") or clean_path == "health":
        raise HTTPException(status_code=404, detail="Not Found")
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
