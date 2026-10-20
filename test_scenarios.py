"""test_scenarios.py - Automated parity verification test suite.

Validates the 5 critical benchmark requirements on FalkorDB (Cloud or Local):
1. at_risk_machines returns M7 and M12.
2. shortfall_check on Product P4 shows a positive deficit gap (> 0).
3. M12's downstream products show NO shortfall (gap == 0) and redundant machines.
4. single_points_of_failure includes the planted PART_SPOF_ALLOY.
5. schedule_action creates a (:Decision) node with [:BASED_ON] edges,
   and properly cleans up test artifacts.
"""

import sys
from core.db import get_connection_config, get_graph
from core.mcp.server import (
    at_risk_machines,
    downstream_impact,
    shortfall_check,
    single_points_of_failure,
    schedule_action,
)


def run_tests():
    cfg = get_connection_config()
    print("=" * 65)
    print(f"Running Parity Tests on FalkorDB ({cfg['host']}:{cfg['port']})")
    print(f"Target Graph: {cfg['graph_name']} | Environment: {'Cloud' if cfg['is_cloud'] else 'Local'}")
    print("=" * 65)

    passed = 0
    total = 5

    # Test 1: at_risk_machines returns M7 and M12
    print("\n[TEST 1] Testing at_risk_machines(threshold=0.70)...")
    res1 = at_risk_machines(threshold=0.70)
    flagged_ids = [m["machine_id"] for m in res1.get("machines", [])]
    print(f"  Flagged machines: {flagged_ids}")
    if "M7" in flagged_ids and "M12" in flagged_ids:
        print("  ✓ PASS: Both M7 and M12 correctly identified.")
        passed += 1
    else:
        print(f"  ✗ FAIL: Expected M7 and M12 in {flagged_ids}")

    # Test 2: shortfall_check on P4 shows positive gap
    print("\n[TEST 2] Testing shortfall_check('P4')...")
    res2 = shortfall_check("P4")
    gap = res2.get("shortfall_units", 0)
    print(f"  P4 30d forecast: {res2.get('forecast_30d')}, Total stock: {res2.get('total_stock')}, Shortfall: {gap}")
    if gap > 0 and res2.get("has_critical_shortfall"):
        print(f"  ✓ PASS: P4 exhibits critical positive shortfall of {gap} units.")
        passed += 1
    else:
        print(f"  ✗ FAIL: P4 shortfall is {gap}, expected positive deficit.")

    # Test 3: M12's downstream products show no shortfall & redundant machines
    print("\n[TEST 3] Testing downstream impact and shortfall for M12...")
    impact_m12 = downstream_impact("M12")
    m12_prods = impact_m12.get("affected_products", [])
    m12_shortfall_total = 0
    for p in m12_prods:
        sc = shortfall_check(p["id"])
        m12_shortfall_total += sc.get("shortfall_units", 0)
    
    is_sole = impact_m12.get("is_sole_producer", True)
    print(f"  M12 affected products: {[p['id'] for p in m12_prods]}")
    print(f"  M12 total downstream shortfall: {m12_shortfall_total}")
    print(f"  M12 is sole producer: {is_sole}")
    if m12_shortfall_total == 0 and not is_sole:
        print("  ✓ PASS: M12 has 0 shortfall and redundant backup machines.")
        passed += 1
    else:
        print("  ✗ FAIL: M12 should have 0 shortfall and redundant machine producers.")

    # Test 4: single_points_of_failure includes planted part
    print("\n[TEST 4] Testing single_points_of_failure()...")
    res4 = single_points_of_failure()
    spof_parts = [p["part_id"] for p in res4.get("single_points_of_failure", [])]
    print(f"  Total SPOF components detected: {len(spof_parts)}")
    if "PART_SPOF_ALLOY" in spof_parts:
        print("  ✓ PASS: Planted PART_SPOF_ALLOY successfully flagged.")
        passed += 1
    else:
        print(f"  ✗ FAIL: PART_SPOF_ALLOY not found in {spof_parts[:5]}...")

    # Test 5: schedule_action creates Decision node with BASED_ON edges & cleans up
    print("\n[TEST 5] Testing schedule_action and evidence grounding...")
    test_target = "M7"
    test_evidence = ["M7", "P4", "PART_M7_ROTOR"]
    action_res = schedule_action(
        type="schedule_maintenance",
        target_id=test_target,
        reason="Automated Parity Test Decision",
        evidence_ids=test_evidence,
    )
    dec_id = action_res.get("decision_id")
    linked_count = action_res.get("linked_evidence_count", 0)
    print(f"  Created test decision: {dec_id} with {linked_count} linked evidence nodes")

    # Verify directly via Cypher
    g = get_graph()
    verify_res = g.query(
        "MATCH (d:Decision {id: $d_id})-[r:BASED_ON]->(t) RETURN count(r)",
        params={"d_id": dec_id}
    ).result_set
    edges_in_graph = verify_res[0][0] if verify_res else 0

    # Cleanup test decision
    g.query("MATCH (d:Decision {id: $d_id}) DETACH DELETE d", params={"d_id": dec_id})
    print("  Cleaned up test decision from graph.")

    if edges_in_graph == len(test_evidence):
        print(f"  ✓ PASS: Decision {dec_id} verified with {edges_in_graph} BASED_ON edges.")
        passed += 1
    else:
        print(f"  ✗ FAIL: Expected {len(test_evidence)} edges, found {edges_in_graph}")

    print("\n" + "=" * 65)
    print(f"PARITY SUITE RESULTS: {passed}/{total} TESTS PASSED")
    print("=" * 65)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_tests())
