"""reset_decisions.py - Deletes all (:Decision) nodes from the graph.

Allows resetting operational decisions to a clean slate before running a live demo.
"""

import sys
from db import get_graph, get_connection_config


def reset_decisions():
    cfg = get_connection_config()
    print(f"Connecting to FalkorDB graph '{cfg['graph_name']}' on {cfg['host']}:{cfg['port']}...")
    g = get_graph()

    # Count existing decisions
    count_res = g.query("MATCH (d:Decision) RETURN count(d)").result_set
    before_count = count_res[0][0] if count_res else 0
    print(f"Found {before_count} active Decision node(s).")

    # Delete all decisions and their incident edges
    g.query("MATCH (d:Decision) DETACH DELETE d")

    # Verify
    verify_res = g.query("MATCH (d:Decision) RETURN count(d)").result_set
    after_count = verify_res[0][0] if verify_res else 0

    print(f"✓ Successfully deleted all Decision nodes. Remaining: {after_count}")
    return after_count == 0


if __name__ == "__main__":
    success = reset_decisions()
    sys.exit(0 if success else 1)
