"""mcp_server.py - Backward-compatible wrapper for core.mcp.server."""
from core.mcp.server import (
    TOOL_DISPATCH,
    CLAUDE_TOOLS,
    at_risk_machines,
    downstream_impact,
    shortfall_check,
    single_points_of_failure,
    alternate_sources,
    shortest_path,
    schedule_action,
    mcp_app,
)

__all__ = [
    "TOOL_DISPATCH",
    "CLAUDE_TOOLS",
    "at_risk_machines",
    "downstream_impact",
    "shortfall_check",
    "single_points_of_failure",
    "alternate_sources",
    "shortest_path",
    "schedule_action",
    "mcp_app",
]

if __name__ == "__main__":
    from core.mcp.server import at_risk_machines, downstream_impact, shortfall_check, alternate_sources, shortest_path
    print("Testing MCP tools directly via core.mcp.server...")
    print("\n1. at_risk_machines(0.70):")
    arm = at_risk_machines(0.70)
    print(f"Found {arm['count']} machines: {[m['machine_id'] for m in arm['machines']]}")
