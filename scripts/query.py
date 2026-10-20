"""scripts/query.py - CLI tool to run Cypher queries directly against FalkorDB.

Usage:
    ./.venv/bin/python3 scripts/query.py "MATCH (n) RETURN labels(n), count(n)"
    ./.venv/bin/python3 scripts/query.py "MATCH (m:Machine) RETURN m.id, m.name, m.failure_risk LIMIT 10"
"""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.db import get_graph


def main():
    if len(sys.argv) < 2:
        query = "MATCH (n) RETURN DISTINCT labels(n)[0] AS Label, count(n) AS Count"
        print(f"No Cypher query provided. Running default overview query:\n{query}\n")
    else:
        query = " ".join(sys.argv[1:])

    try:
        g = get_graph()
        result = g.query(query)

        header = result.header
        rows = result.result_set

        if header:
            # Format as clean table
            cols = [h[1] if isinstance(h, (list, tuple)) and len(h) > 1 else str(h) for h in header]
            str_rows = [[str(cell) for cell in row] for row in rows]
            col_widths = [max(len(cols[i]), max((len(r[i]) for r in str_rows), default=0)) for i in range(len(cols))]

            # Print header
            header_str = " | ".join(cols[i].ljust(col_widths[i]) for i in range(len(cols)))
            divider = "-+-".join("-" * col_widths[i] for i in range(len(cols)))
            print(header_str)
            print(divider)

            # Print rows
            for r in str_rows:
                print(" | ".join(r[i].ljust(col_widths[i]) for i in range(len(r))))

            print(f"\n({len(rows)} row{'s' if len(rows) != 1 else ''})")
        else:
            print(rows)
    except Exception as e:
        print(f"Error executing Cypher query: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
