"""core/api package - Modular FastAPI Routers for the Supply Chain Digital Twin."""

from core.api.routes_telemetry import router as telemetry_router
from core.api.routes_simulation import router as simulation_router
from core.api.routes_agent import router as agent_router
from core.api.routes_decisions import router as decisions_router
from core.api.routes_copilot import router as copilot_router

__all__ = [
    "telemetry_router",
    "simulation_router",
    "agent_router",
    "decisions_router",
    "copilot_router",
]
