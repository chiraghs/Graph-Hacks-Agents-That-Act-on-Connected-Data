"""scripts/seed.py - High-speed idempotent UNWIND batch graph seeder CLI."""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.graph.seed import seed_database, get_connection_config

if __name__ == "__main__":
    cfg = get_connection_config()
    print(f"Seeding FalkorDB graph '{cfg['graph_name']}' on {cfg['host']}:{cfg['port']}...")
    summary = seed_database()
    print("Seed Complete! Verification Counts:")
    for k, v in summary.items():
        print(f"  {k:20s}: {v}")
