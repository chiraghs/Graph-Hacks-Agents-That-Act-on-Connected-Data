# Cypher Query Catalog & Relational Multi-Join Comparison

This document catalogs every Cypher query executed by the **Supply Chain Intelligence Agent** backed by **FalkorDB**, explaining why equivalent operations in relational SQL require painful, fragile, and slow multi-table joins.

---

### 1. Identify Assets with Predictive Maintenance Risk
```cypher
MATCH (pl:Plant)-[:HAS]->(m:Machine)
WHERE m.failure_risk >= $threshold
RETURN m.id AS machine_id, m.name AS machine_name,
       m.failure_risk AS failure_risk,
       m.predicted_failure_days AS predicted_failure_days,
       pl.id AS plant_id, pl.name AS plant_name, pl.location AS plant_location
ORDER BY m.failure_risk DESC
```
- **Explanation**: Traverses the manufacturing topology to find machines exceeding sensor-drift risk thresholds along with their plant locations.
- **Why painful in SQL**: In SQL, this requires joining `plants`, `machine_plants`, and `machines` tables. In a graph, hierarchical containment `(:Plant)-[:HAS]->(:Machine)` is a natural pointer traversal with zero index lookups on foreign keys.

---

### 2. Multi-Hop Downstream E2E Impact Traversal
```cypher
MATCH (m:Machine {id: $m_id})-[:PRODUCES]->(pt:Part)-[:USED_IN]->(prod:Product)-[:STOCKED_AT]->(wh:Warehouse)-[:SERVES]->(c:Customer)
RETURN pt.id AS part_id, pt.name AS part_name,
       prod.id AS product_id, prod.name AS product_name, prod.forecast_30d AS forecast_30d,
       wh.id AS warehouse_id, wh.name AS warehouse_name,
       c.id AS customer_id, c.name AS customer_name, c.tier AS customer_tier
```
- **Explanation**: Performs a 5-hop variable-length graph traversal tracing from an affected machine through its manufactured parts, assembled products, regional warehouses, and downstream enterprise customers.
- **Why painful in SQL**: In relational databases, this query demands joining **9 separate tables**: `machines` ➔ `machine_parts` ➔ `parts` ➔ `bill_of_materials` ➔ `products` ➔ `inventory_allocations` ➔ `warehouses` ➔ `warehouse_customers` ➔ `customers`. As data volume grows, multi-table Cartesian joins degrade exponentially, whereas FalkorDB traverses direct memory pointers in constant time per hop.

---

### 3. Redundancy & Alternate Machine Production Verification
```cypher
MATCH (m:Machine {id: $m_id})-[:PRODUCES]->(pt:Part)
OPTIONAL MATCH (other:Machine)-[:PRODUCES]->(pt)
WHERE other.id <> $m_id
RETURN pt.id AS part_id, collect(other.id) AS alternate_machines
```
- **Explanation**: Identifies whether parts produced by a failing machine have alternate machine production lines available anywhere in the global network.
- **Why painful in SQL**: Requires self-joining the `machine_parts` mapping table on `part_id` with `WHERE machine_id != $m_id`, followed by a `GROUP BY` and string concatenation aggregation, which quickly becomes an index scan bottleneck.

---

### 4. Demand Shortfall vs Available Warehouse Inventory
```cypher
MATCH (prod:Product {id: $p_id})
OPTIONAL MATCH (prod)-[s:STOCKED_AT]->(wh:Warehouse)
RETURN prod.id AS product_id, prod.name AS product_name,
       prod.forecast_30d AS forecast_30d,
       prod.safety_stock AS safety_stock,
       coalesce(sum(s.qty), 0) AS total_stock,
       collect({warehouse_id: wh.id, warehouse_name: wh.name, stock_qty: s.qty}) AS allocations
```
- **Explanation**: Aggregates distributed inventory across multiple warehouses to compare total available buffer stock against 30-day forecast demand.
- **Why painful in SQL**: Requires joining products with warehouse inventory tables, managing null handling (`COALESCE`), and performing array/JSON aggregation for breakdown views.

---

### 5. Global Single Point of Failure (SPOF) Detection
```cypher
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
```
- **Explanation**: Scans the entire topology to detect parts that rely on a single external supplier OR a single internal manufacturing unit.
- **Why painful in SQL**: In SQL, detecting bidirectional bottlenecks requires two independent `LEFT OUTER JOIN`s across `supplier_parts` and `machine_parts`, followed by complex `HAVING` and `GROUP BY` clauses that cause heavy temporary table allocation and full table scans.

---

### 6. Alternate Suppliers & Emergency Lead Times
```cypher
MATCH (pt:Part {id: $part_id})
OPTIONAL MATCH (s:Supplier)-[sup_rel:SUPPLIES]->(pt)
OPTIONAL MATCH (s)-[:ALTERNATE_FOR]->(alt_sup:Supplier)
OPTIONAL MATCH (alt_sup)-[alt_rel:SUPPLIES]->(pt)
OPTIONAL MATCH (m:Machine)-[:PRODUCES]->(pt)
RETURN pt.id AS part_id,
       collect(DISTINCT {id: s.id, name: s.name, lead_time_days: sup_rel.lead_time_days}) AS direct_suppliers,
       collect(DISTINCT {id: alt_sup.id, name: alt_sup.name, lead_time_days: alt_rel.lead_time_days}) AS alternate_suppliers,
       collect(DISTINCT {id: m.id, name: m.name, failure_risk: m.failure_risk, predicted_failure_days: m.predicted_failure_days}) AS producing_machines
```
- **Explanation**: Discovers substitute suppliers connected via peer relationships `(:Supplier)-[:ALTERNATE_FOR]->(:Supplier)` and compares their procurement lead times against internal machine breakdown deadlines.
- **Why painful in SQL**: Peer substitution in relational models requires an auxiliary mapping table with bidirectional lookup queries, multiple self-joins, and union operations.

---

### 7. Variable-Length Shortest Dependency Path
```cypher
MATCH (a {id: $a_id}), (b {id: $b_id})
MATCH p = (a)-[*1..6]-(b)
RETURN [n in nodes(p) | {id: n.id, label: labels(n)[0], name: n.name}] AS path_nodes,
       [r in relationships(p) | type(r)] AS path_edges,
       length(p) AS hops
ORDER BY hops ASC
LIMIT 1
```
- **Explanation**: Explains the exact relational chain linking any two disparate entities (e.g., failing Machine M7 to affected Customer CUST_001) in the network.
- **Why painful in SQL**: Variable-length shortest-path traversal across diverse entity types is virtually impossible in standard SQL without recursive Common Table Expressions (`WITH RECURSIVE`), which are notorious for infinite loops, quadratic complexity, and poor performance. In FalkorDB, BFS graph traversal resolves in milliseconds.

---

### 8. Auditable Decision Node Creation & Evidence Grounding
```cypher
CREATE (d:Decision {
    id: $id,
    type: $type,
    target: $target,
    reason: $reason,
    ts: $ts
})
```
```cypher
MATCH (d:Decision {id: $d_id})
MATCH (target {id: $ev_id})
CREATE (d)-[:BASED_ON]->(target)
```
- **Explanation**: Creates an immutable decision node and connects it with `[:BASED_ON]` relationships to polymorphic evidence nodes (Machines, Parts, Products, Warehouses, Suppliers).
- **Why painful in SQL**: In SQL, polymorphic foreign keys (linking a single decision to rows across 5 different tables) violate relational integrity and require multiple nullable foreign key columns (`machine_id`, `product_id`, `part_id`, `supplier_id`) or an unwieldy generic association table. In FalkorDB, `[:BASED_ON]` edges link to any node label transparently.
