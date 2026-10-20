"""scripts/check_connection.py - Verifies connectivity to FalkorDB (Cloud or Local)."""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.db import get_connection_config, get_graph, get_db


def main():
    cfg = get_connection_config()
    print("=" * 60)
    print("FalkorDB Connection Diagnostic")
    print("=" * 60)
    print(f"Target Host : {cfg['host']}:{cfg['port']}")
    print(f"SSL/TLS     : {'Enabled' if cfg['ssl'] else 'Disabled'}")
    print(f"Auth Mode   : {'Authenticated' if cfg['password'] else 'No Password (Local Default)'}")
    print(f"Target Graph: {cfg['graph_name']}")
    print(f"Environment : {'Cloud Instance' if cfg['is_cloud'] else 'Local Docker'}")
    print("-" * 60)

    try:
        print("Testing socket ping...")
        db = get_db()
        print("✓ Ping successful!")

        print(f"Connecting to graph '{cfg['graph_name']}'...")
        graph = get_graph()

        print("Executing test query: RETURN 1 ...")
        res = graph.query("RETURN 1 AS ping").result_set
        print(f"✓ Query response: {res}")

        print("Querying graph node count...")
        node_res = graph.query("MATCH (n) RETURN count(n) AS node_count").result_set
        node_count = node_res[0][0] if node_res else 0
        print(f"✓ Current Node Count: {node_count}")

        print("-" * 60)
        print("STATUS: Connection verified successfully!")
        print("=" * 60)
        return 0
    except Exception as e:
        print("\n❌ CONNECTION FAILED!")
        print(f"Details: {e}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
