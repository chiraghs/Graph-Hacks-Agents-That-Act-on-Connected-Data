"""db.py - Backward-compatible wrapper for core.db."""
from core.db import get_connection_config, get_db, get_graph

__all__ = ["get_connection_config", "get_db", "get_graph"]
