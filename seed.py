"""seed.py - Backward-compatible wrapper for core.graph.seed."""
from core.graph.seed import (
    seed_database,
    build_synthetic_dataset,
    get_connection_config,
)

__all__ = ["seed_database", "build_synthetic_dataset"]

if __name__ == "__main__":
    cfg = get_connection_config()
    print(f"Seeding FalkorDB graph '{cfg['graph_name']}' on {cfg['host']}:{cfg['port']}...")
    summary = seed_database()
    print("Seed Complete! Verification Counts:")
    for k, v in summary.items():
        print(f"  {k:20s}: {v}")
