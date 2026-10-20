"""scripts/reset_decisions.py - Utility to purge all Decision nodes for clean demo resets."""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.db import get_graph, get_connection_config


def reset_decisions():
    cfg = get_connection_config()
    print(f"Connecting to FalkorDB graph '{cfg['graph_name']}' on {cfg['host']}:{cfg['port']}...")
    graph = get_graph()
    
    count_res = graph.query("MATCH (d:Decision) RETURN count(d)").result_set
    count = count_res[0][0] if count_res else 0
    print(f"Found {count} active Decision node(s).")
    
    if count > 0:
        graph.query("MATCH (d:Decision) DETACH DELETE d")
        print(f"✓ Successfully deleted all Decision nodes. Remaining: 0")
    else:
        print("✓ Graph is already clear of Decision nodes.")


if __name__ == "__main__":
    reset_decisions()
