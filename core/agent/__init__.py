"""core/agent package - Autonomous multi-hop graph reasoning and SSE investigation streamer."""
from core.agent.runner import (
    run_autonomous_investigation,
    stream_investigation,
    SYSTEM_PROMPT,
)

__all__ = [
    "run_autonomous_investigation",
    "stream_investigation",
    "SYSTEM_PROMPT",
]
