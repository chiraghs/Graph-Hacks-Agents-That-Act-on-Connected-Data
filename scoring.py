"""scoring.py - Backward-compatible wrapper for core.graph.scoring."""
from core.graph.scoring import (
    compute_machine_risk,
    compute_demand_forecast,
    compute_safety_stock,
)

__all__ = [
    "compute_machine_risk",
    "compute_demand_forecast",
    "compute_safety_stock",
]
