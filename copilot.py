"""copilot.py - Backward-compatible wrapper for core.copilot.service."""
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

if __name__ == "__main__":
    queries = [
        "Which machines have high failure risk?",
        "What products are affected if M7 fails?",
        "Are there alternate suppliers for rotor parts?",
    ]
    for q in queries:
        print(f"\nQuery: {q}")
        res = ask_copilot(q)
        print(f"Provider: {res.get('provider')} ({res.get('model')})")
        print(f"Cypher: {res.get('cypher')}")
        print(f"Answer: {res.get('answer')}")
