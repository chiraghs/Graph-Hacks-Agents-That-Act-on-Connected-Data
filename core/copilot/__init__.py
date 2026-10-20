"""core/copilot package - Multi-provider Natural Language to Cypher Graph Copilot."""
from core.copilot.service import (
    ask_copilot,
    GRAPH_SCHEMA,
    SYSTEM_PROMPT,
)

__all__ = [
    "ask_copilot",
    "GRAPH_SCHEMA",
    "SYSTEM_PROMPT",
]
