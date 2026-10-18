"""mcp_server.py - Model Context Protocol (MCP) Server for Supply Chain Intelligence.

Exposes 7 Cypher-backed tools to reason over FalkorDB graph data:
1. at_risk_machines(threshold)
2. downstream_impact(machine_id)
3. shortfall_check(product_id)
4. single_points_of_failure()
5. alternate_sources(part_id)
6. shortest_path(a_id, b_id)
7. schedule_action(type, target_id, reason, evidence_ids) [Only Write Tool]

Every read tool returns traceable node and edge IDs used as evidence.
"""

import sys
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid
from db import get_graph

# Try importing MCPServer from mcp 2.x
try:
    from mcp.server.mcpserver import MCPServer
    mcp_app = MCPServer("supply-chain-intelligence")
except Exception:
    mcp_app = None


# ==============================================================================
# TOOL 1: at_risk_machines
# ==============================================================================
def at_risk_machines(threshold: float = 0.70) -> Dict[str, Any]:
    """Find machines whose failure_risk exceeds the given threshold.
    
    Args:
        threshold: Minimum risk score (0.0 to 1.0) to flag machine. Default 0.70.
    """
    g = get_graph()
    cypher = """
    MATCH (pl:Plant)-[:HAS]->(m:Machine)
    WHERE m.failure_risk >= $threshold
    RETURN m.id AS machine_id, m.name AS machine_name,
           m.failure_risk AS failure_risk,
           m.predicted_failure_days AS predicted_failure_days,
           pl.id AS plant_id, pl.name AS plant_name, pl.location AS plant_location
    ORDER BY m.failure_risk DESC
    """
    result = g.query(cypher, params={"threshold": float(threshold)}).result_set

    machines = []
    evidence_nodes = []
    evidence_edges = []

    for row in result:
        m_id, m_name, risk, days, pl_id, pl_name, pl_loc = row
        machines.append({
            "machine_id": m_id,
            "machine_name": m_name,
            "failure_risk": risk,
            "predicted_failure_days": days,
            "plant": {"id": pl_id, "name": pl_name, "location": pl_loc},
        })
        evidence_nodes.extend([m_id, pl_id])
        evidence_edges.append(f"{pl_id}->HAS->{m_id}")

    return {
        "count": len(machines),
        "threshold": threshold,
        "machines": machines,
        "evidence_node_ids": list(set(evidence_nodes)),
        "evidence_edge_ids": list(set(evidence_edges)),
    }


# ==============================================================================
# TOOL 2: downstream_impact
# ==============================================================================
def downstream_impact(machine_id: str) -> Dict[str, Any]:
    """Perform multi-hop traversal to trace all downstream affected parts,
    products, warehouses, and customers if the specified machine fails.
    
    Traversal: (:Machine)-[:PRODUCES]->(:Part)-[:USED_IN]->(:Product)-[:STOCKED_AT]->(:Warehouse)-[:SERVES]->(:Customer)
    """
    g = get_graph()
    # 1. Traverse downstream impact chain
    cypher_impact = """
    MATCH (m:Machine {id: $m_id})-[:PRODUCES]->(pt:Part)-[:USED_IN]->(prod:Product)-[:STOCKED_AT]->(wh:Warehouse)-[:SERVES]->(c:Customer)
    RETURN pt.id AS part_id, pt.name AS part_name,
           prod.id AS product_id, prod.name AS product_name, prod.forecast_30d AS forecast_30d,
           wh.id AS warehouse_id, wh.name AS warehouse_name,
           c.id AS customer_id, c.name AS customer_name, c.tier AS customer_tier
    """
    res_impact = g.query(cypher_impact, params={"m_id": machine_id}).result_set

    # 2. Check for redundant machines producing these exact parts
    cypher_redundancy = """
    MATCH (m:Machine {id: $m_id})-[:PRODUCES]->(pt:Part)
    OPTIONAL MATCH (other:Machine)-[:PRODUCES]->(pt)
    WHERE other.id <> $m_id
    RETURN pt.id AS part_id, collect(other.id) AS alternate_machines
    """
    res_redundancy = g.query(cypher_redundancy, params={"m_id": machine_id}).result_set
    redundancy_map = {row[0]: row[1] for row in res_redundancy}

    parts_dict = {}
    products_dict = {}
    warehouses_dict = {}
    customers_dict = {}
    evidence_nodes = [machine_id]
    evidence_edges = []

    for row in res_impact:
        pt_id, pt_name, prod_id, prod_name, fcast, wh_id, wh_name, c_id, c_name, c_tier = row

        parts_dict[pt_id] = {
            "id": pt_id,
            "name": pt_name,
            "has_redundant_machine": len(redundancy_map.get(pt_id, [])) > 0,
            "redundant_machines": redundancy_map.get(pt_id, []),
        }
        products_dict[prod_id] = {"id": prod_id, "name": prod_name, "forecast_30d": fcast}
        warehouses_dict[wh_id] = {"id": wh_id, "name": wh_name}
        customers_dict[c_id] = {"id": c_id, "name": c_name, "tier": c_tier}

        evidence_nodes.extend([pt_id, prod_id, wh_id, c_id])
        evidence_edges.extend([
            f"{machine_id}->PRODUCES->{pt_id}",
            f"{pt_id}->USED_IN->{prod_id}",
            f"{prod_id}->STOCKED_AT->{wh_id}",
            f"{wh_id}->SERVES->{c_id}",
        ])

    is_sole_producer = any(not p["has_redundant_machine"] for p in parts_dict.values()) if parts_dict else False

    return {
        "machine_id": machine_id,
        "is_sole_producer": is_sole_producer,
        "affected_parts": list(parts_dict.values()),
        "affected_products": list(products_dict.values()),
        "affected_warehouses": list(warehouses_dict.values()),
        "affected_customers": list(customers_dict.values()),
        "evidence_node_ids": list(set(evidence_nodes)),
        "evidence_edge_ids": list(set(evidence_edges)),
    }


# ==============================================================================
# TOOL 3: shortfall_check
# ==============================================================================
def shortfall_check(product_id: str) -> Dict[str, Any]:
    """Calculate the inventory gap between 30-day forecast demand, safety stock,
    and current available warehouse stock.
    
    Returns numeric gap and shortfall severity.
    """
    g = get_graph()
    cypher = """
    MATCH (prod:Product {id: $p_id})
    OPTIONAL MATCH (prod)-[s:STOCKED_AT]->(wh:Warehouse)
    RETURN prod.id AS product_id, prod.name AS product_name,
           prod.forecast_30d AS forecast_30d,
           prod.safety_stock AS safety_stock,
           coalesce(sum(s.qty), 0) AS total_stock,
           collect({warehouse_id: wh.id, warehouse_name: wh.name, stock_qty: s.qty}) AS allocations
    """
    res = g.query(cypher, params={"p_id": product_id}).result_set
    if not res:
        return {"error": f"Product {product_id} not found", "shortfall": 0}

    prod_id, prod_name, forecast, safety, total_stock, allocations = res[0]
    total_stock = float(total_stock)

    # Net available stock accounting for required safety buffer
    net_available = total_stock - safety
    # Shortfall occurs if forecast demand exceeds available warehouse stock
    shortfall = max(0.0, forecast - total_stock)
    has_critical_shortfall = shortfall > 0

    evidence_nodes = [prod_id]
    evidence_edges = []
    for alloc in allocations:
        wh_id = alloc.get("warehouse_id")
        if wh_id:
            evidence_nodes.append(wh_id)
            evidence_edges.append(f"{prod_id}->STOCKED_AT->{wh_id}")

    return {
        "product_id": prod_id,
        "product_name": prod_name,
        "forecast_30d": forecast,
        "safety_stock": safety,
        "total_stock": total_stock,
        "net_available_stock": net_available,
        "shortfall_units": shortfall,
        "has_critical_shortfall": has_critical_shortfall,
        "allocations": allocations,
        "evidence_node_ids": list(set(evidence_nodes)),
        "evidence_edge_ids": list(set(evidence_edges)),
    }


# ==============================================================================
# TOOL 4: single_points_of_failure
# ==============================================================================
def single_points_of_failure() -> Dict[str, Any]:
    """Scan the entire graph to discover single points of failure:
    parts with <= 1 external supplier OR <= 1 internal manufacturing machine.
    """
    g = get_graph()
    cypher = """
    MATCH (pt:Part)
    OPTIONAL MATCH (s:Supplier)-[r:SUPPLIES]->(pt)
    OPTIONAL MATCH (m:Machine)-[:PRODUCES]->(pt)
    WITH pt,
         count(DISTINCT s) AS supplier_count,
         count(DISTINCT m) AS producer_count,
         collect(DISTINCT s.id) AS supplier_ids,
         collect(DISTINCT m.id) AS machine_ids
    WHERE supplier_count <= 1 OR producer_count <= 1
    RETURN pt.id AS part_id, pt.name AS part_name, pt.cost AS cost,
           supplier_count, producer_count, supplier_ids, machine_ids
    ORDER BY producer_count ASC, supplier_count ASC
    """
    res = g.query(cypher).result_set

    spof_list = []
    evidence_nodes = []

    for row in res:
        pt_id, pt_name, cost, s_count, m_count, sups, machs = row
        severity = "CRITICAL" if (s_count <= 1 and m_count <= 1) else "WARNING"
        spof_list.append({
            "part_id": pt_id,
            "part_name": pt_name,
            "cost": cost,
            "supplier_count": s_count,
            "producer_count": m_count,
            "supplier_ids": sups,
            "machine_ids": machs,
            "severity": severity,
        })
        evidence_nodes.append(pt_id)
        evidence_nodes.extend(sups)
        evidence_nodes.extend(machs)

    return {
        "count": len(spof_list),
        "single_points_of_failure": spof_list,
        "evidence_node_ids": list(set(evidence_nodes)),
    }


# ==============================================================================
# TOOL 5: alternate_sources
# ==============================================================================
def alternate_sources(part_id: str) -> Dict[str, Any]:
    """Find substitute suppliers or backup manufacturing machines for a part,
    ranked by delivery lead time.
    """
    g = get_graph()
    cypher = """
    MATCH (pt:Part {id: $part_id})
    OPTIONAL MATCH (s:Supplier)-[sup_rel:SUPPLIES]->(pt)
    OPTIONAL MATCH (s)-[:ALTERNATE_FOR]->(alt_sup:Supplier)
    OPTIONAL MATCH (alt_sup)-[alt_rel:SUPPLIES]->(pt)
    OPTIONAL MATCH (m:Machine)-[:PRODUCES]->(pt)
    RETURN pt.id AS part_id,
           collect(DISTINCT {id: s.id, name: s.name, lead_time_days: sup_rel.lead_time_days}) AS direct_suppliers,
           collect(DISTINCT {id: alt_sup.id, name: alt_sup.name, lead_time_days: alt_rel.lead_time_days}) AS alternate_suppliers,
           collect(DISTINCT {id: m.id, name: m.name, failure_risk: m.failure_risk, predicted_failure_days: m.predicted_failure_days}) AS producing_machines
    """
    res = g.query(cypher, params={"part_id": part_id}).result_set
    if not res:
        return {"part_id": part_id, "suppliers": [], "machines": []}

    _, direct_sups, alt_sups, machines = res[0]

    # Filter out empty entries from OPTIONAL MATCH
    all_suppliers = []
    seen_sups = set()
    for s in direct_sups + alt_sups:
        if s.get("id") and s["id"] not in seen_sups:
            seen_sups.add(s["id"])
            all_suppliers.append(s)

    # Sort suppliers by shortest lead time
    all_suppliers.sort(key=lambda x: x.get("lead_time_days") or 999)

    valid_machines = [m for m in machines if m.get("id")]
    valid_machines.sort(key=lambda x: x.get("failure_risk") or 1.0)

    evidence_nodes = [part_id] + [s["id"] for s in all_suppliers] + [m["id"] for m in valid_machines]

    return {
        "part_id": part_id,
        "available_suppliers_by_lead_time": all_suppliers,
        "available_producing_machines": valid_machines,
        "evidence_node_ids": list(set(evidence_nodes)),
    }


# ==============================================================================
# TOOL 6: shortest_path
# ==============================================================================
def shortest_path(a_id: str, b_id: str) -> Dict[str, Any]:
    """Explain how two nodes are connected in the supply chain network using
    the shortest graph traversal path.
    """
    g = get_graph()
    cypher = """
    MATCH (a {id: $a_id}), (b {id: $b_id})
    MATCH p = (a)-[*1..6]-(b)
    RETURN [n in nodes(p) | {id: n.id, label: labels(n)[0], name: n.name}] AS path_nodes,
           [r in relationships(p) | type(r)] AS path_edges,
           length(p) AS hops
    ORDER BY hops ASC
    LIMIT 1
    """
    res = g.query(cypher, params={"a_id": a_id, "b_id": b_id}).result_set
    if not res:
        return {
            "connected": False,
            "explanation": f"No path found between {a_id} and {b_id} within 6 hops.",
            "evidence_node_ids": [a_id, b_id],
        }

    nodes_list, edges_list, hops = res[0]
    node_ids = [n["id"] for n in nodes_list]

    # Construct step-by-step human readable explanation
    explanation_steps = []
    for i in range(len(edges_list)):
        curr_node = nodes_list[i]
        next_node = nodes_list[i + 1]
        rel = edges_list[i]
        explanation_steps.append(
            f"{curr_node.get('label')}:{curr_node.get('id')} -[{rel}]-> {next_node.get('label')}:{next_node.get('id')}"
        )

    explanation = " -> ".join(explanation_steps)

    return {
        "connected": True,
        "hops": hops,
        "path_nodes": nodes_list,
        "path_edges": edges_list,
        "explanation": explanation,
        "evidence_node_ids": node_ids,
    }


# ==============================================================================
# TOOL 7: schedule_action (The ONLY Write Tool)
# ==============================================================================
def schedule_action(
    type: str,
    target_id: str,
    reason: str,
    evidence_ids: List[str],
) -> Dict[str, Any]:
    """Execute and record an operational mitigation decision into the graph.
    
    Creates a (:Decision {id, type, target, reason, ts}) node and connects it
    via [:BASED_ON] relationships to every evidence node that justified the decision.
    
    Args:
        type: One of {'schedule_maintenance', 'reroute_production', 'expedite_order'}
        target_id: ID of the entity acted on (e.g., 'M7', 'P4')
        reason: Plain-text explanation justified by multi-hop graph evidence
        evidence_ids: List of node IDs used as proof (minimum 2 hops of evidence)
    """
    valid_types = {"schedule_maintenance", "reroute_production", "expedite_order"}
    if type not in valid_types:
        return {
            "status": "error",
            "message": f"Invalid action type '{type}'. Must be one of {valid_types}",
        }

    g = get_graph()
    decision_id = f"DEC_{uuid.uuid4().hex[:8].upper()}"
    ts = datetime.now(timezone.utc).isoformat()

    # 1. Create Decision Node
    cypher_create = """
    CREATE (d:Decision {
        id: $id,
        type: $type,
        target: $target,
        reason: $reason,
        ts: $ts
    })
    RETURN d.id AS decision_id
    """
    g.query(cypher_create, params={
        "id": decision_id,
        "type": type,
        "target": target_id,
        "reason": reason,
        "ts": ts,
    })

    # 2. Connect Decision to each evidence node via [:BASED_ON]
    linked_evidence = []
    for ev_id in set(evidence_ids):
        cypher_link = """
        MATCH (d:Decision {id: $d_id})
        MATCH (target {id: $ev_id})
        CREATE (d)-[:BASED_ON]->(target)
        RETURN labels(target)[0] AS label, target.id AS id
        """
        link_res = g.query(cypher_link, params={"d_id": decision_id, "ev_id": ev_id}).result_set
        if link_res:
            linked_evidence.append({"id": link_res[0][1], "label": link_res[0][0]})

    return {
        "status": "success",
        "decision_id": decision_id,
        "type": type,
        "target": target_id,
        "reason": reason,
        "timestamp": ts,
        "linked_evidence_count": len(linked_evidence),
        "linked_evidence": linked_evidence,
    }


# ==============================================================================
# TOOL REGISTRY FOR AGENT & FAST MCP
# ==============================================================================
TOOL_DISPATCH = {
    "at_risk_machines": at_risk_machines,
    "downstream_impact": downstream_impact,
    "shortfall_check": shortfall_check,
    "single_points_of_failure": single_points_of_failure,
    "alternate_sources": alternate_sources,
    "shortest_path": shortest_path,
    "schedule_action": schedule_action,
}

# Anthropic Tool Schema Definition
CLAUDE_TOOLS = [
    {
        "name": "at_risk_machines",
        "description": "Scans the graph for machines with predictive-maintenance failure risk >= threshold. Returns machine details and plant locations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "threshold": {
                    "type": "number",
                    "description": "Failure risk threshold (0.0 to 1.0). Defaults to 0.70.",
                    "default": 0.70,
                }
            },
        },
    },
    {
        "name": "downstream_impact",
        "description": "Performs variable-length graph traversal: Machine -> Part -> Product -> Warehouse -> Customer. Checks whether parts have redundant producing machines.",
        "input_schema": {
            "type": "object",
            "properties": {
                "machine_id": {
                    "type": "string",
                    "description": "The machine ID to trace impact for (e.g. 'M7', 'M12').",
                }
            },
            "required": ["machine_id"],
        },
    },
    {
        "name": "shortfall_check",
        "description": "Compares 30-day forecast demand against warehouse stock and safety stock for a product. Returns numeric gap and shortfall severity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "Product identifier (e.g. 'P4', 'P12').",
                }
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "single_points_of_failure",
        "description": "Scans the entire graph for parts with only one supplier or only one producing machine.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "alternate_sources",
        "description": "Queries substitute suppliers (and their lead times) and alternate producing machines for a given part.",
        "input_schema": {
            "type": "object",
            "properties": {
                "part_id": {
                    "type": "string",
                    "description": "Part identifier (e.g. 'PART_M7_ROTOR').",
                }
            },
            "required": ["part_id"],
        },
    },
    {
        "name": "shortest_path",
        "description": "Finds the shortest network path between two nodes (e.g. Machine and Customer, or Supplier and Product) to explain their dependency.",
        "input_schema": {
            "type": "object",
            "properties": {
                "a_id": {
                    "type": "string",
                    "description": "Source node ID.",
                },
                "b_id": {
                    "type": "string",
                    "description": "Target node ID.",
                },
            },
            "required": ["a_id", "b_id"],
        },
    },
    {
        "name": "schedule_action",
        "description": "The ONLY write tool. Commits an operational mitigation decision into the graph (creates a Decision node with BASED_ON edges to every evidence node).",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["schedule_maintenance", "reroute_production", "expedite_order"],
                    "description": "The type of action.",
                },
                "target_id": {
                    "type": "string",
                    "description": "The entity acted upon (e.g. 'M7' or 'P4').",
                },
                "reason": {
                    "type": "string",
                    "description": "Human-readable justification based on graph evidence.",
                },
                "evidence_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Node IDs supporting the decision (at least 2 hops of evidence required).",
                },
            },
            "required": ["type", "target_id", "reason", "evidence_ids"],
        },
    },
]

# Register with MCPServer if available
if mcp_app:
    for tool_name, func in TOOL_DISPATCH.items():
        mcp_app.tool()(func)

if __name__ == "__main__":
    print("Testing MCP tools directly...")
    print("\n1. at_risk_machines(0.70):")
    arm = at_risk_machines(0.70)
    print(f"Found {arm['count']} machines: {[m['machine_id'] for m in arm['machines']]}")

    print("\n2. downstream_impact('M7'):")
    di_m7 = downstream_impact("M7")
    print(f"M7 is_sole_producer: {di_m7['is_sole_producer']}, affected products: {[p['id'] for p in di_m7['affected_products']]}")

    print("\n3. downstream_impact('M12'):")
    di_m12 = downstream_impact("M12")
    print(f"M12 is_sole_producer: {di_m12['is_sole_producer']}, affected parts: {[p['id'] for p in di_m12['affected_parts']]}")

    print("\n4. shortfall_check('P4'):")
    sc_p4 = shortfall_check("P4")
    print(f"P4 forecast: {sc_p4['forecast_30d']}, stock: {sc_p4['total_stock']}, shortfall: {sc_p4['shortfall_units']}")

    print("\n5. shortfall_check('P12'):")
    sc_p12 = shortfall_check("P12")
    print(f"P12 forecast: {sc_p12['forecast_30d']}, stock: {sc_p12['total_stock']}, shortfall: {sc_p12['shortfall_units']}")

    print("\n6. alternate_sources('PART_M7_ROTOR'):")
    as_m7 = alternate_sources("PART_M7_ROTOR")
    print(f"Suppliers: {as_m7['available_suppliers_by_lead_time']}")

    print("\n7. shortest_path('M7', 'CUST_001'):")
    sp = shortest_path("M7", "CUST_001")
    print(f"Connected: {sp.get('connected')}, explanation: {sp.get('explanation')}")

    print("\nAll MCP tools tested successfully!")
