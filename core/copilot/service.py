"""copilot.py - Multi-Provider Natural Language to Cypher Graph Copilot.

Supports:
1. Groq (Meta Llama 3.3 70B) via `GROQ_API_KEY` (Free, 500 t/s)
2. Google Gemini (Gemini 2.0 Flash / 1.5 Flash) via `GEMINI_API_KEY` or `GOOGLE_API_KEY` (Free tier)
3. TwinForge Built-in Semantic Graph Engine (Zero-Key Fallback, always available, <5ms)
"""

import os
import re
import json
import time
import urllib.request
import urllib.error
from core.db import get_graph

# Cypher Knowledge Graph Schema Context
GRAPH_SCHEMA = """
FalkorDB Property Graph Schema:
Graph Name: supply_chain (175 nodes, 465 relationships)

Node Labels & Properties:
- Plant: {id, name, location, capacity_utilization, status}
- Machine: {id (e.g. M7, M12), name, failure_risk (0.0-1.0), predicted_failure_days (int), type, vibration, temperature}
- Part: {id (e.g. PT-4, PART_M7_ROTOR), name, single_point_of_failure (bool), lead_time_days}
- Product: {id (e.g. P4, P12), name, demand_units, forecast_30d, safety_stock}
- Warehouse: {id (e.g. WH_MIDWEST, WH_EAST_COAST), name, location, capacity}
- Customer: {id (e.g. CUST_001, ORD-1042), name, sla_tier, penalty_per_day_late}
- Supplier: {id, name, lead_time_days, expedite_cost_multiplier}
- Decision: {id (e.g. DEC_...), type, target, reason, timestamp}

Relationship Types:
- (:Plant)-[:HAS]->(:Machine)
- (:Machine)-[:PRODUCES]->(:Part)
- (:Part)-[:USED_IN {qty_per_unit}]->(:Product)
- (:Product)-[:STOCKED_AT {qty}]->(:Warehouse)
- (:Warehouse)-[:SERVES]->(:Customer)
- (:Supplier)-[:SUPPLIES {lead_time_days}]->(:Part)
- (:Supplier)-[:ALTERNATE_FOR]->(:Supplier)
- (:Decision)-[:BASED_ON]->(:Machine | :Part | :Product | :Warehouse | :Customer | :Supplier)
"""

SYSTEM_PROMPT = f"""You are the TwinForge Graph Copilot, an expert industrial AI assistant connected to a FalkorDB graph database.
Given a user's question, produce a read-only Cypher query and a concise natural language explanation.

{GRAPH_SCHEMA}

RULES:
1. ONLY write read-only Cypher queries (MATCH, WHERE, RETURN, ORDER BY, LIMIT). Never write CREATE, DELETE, SET, or DROP.
2. Return a strict JSON object with two keys:
   "cypher": "<valid Cypher query>"
   "explanation": "<brief summary of what this query discovers in the supply chain>"
3. Keep queries focused and use LIMIT 25 unless counting.
4. Do not include markdown code fences (like ```json), just raw JSON.
"""


def _clean_cypher(query: str) -> str:
    """Sanitizes and enforces read-only safety on Cypher queries."""
    clean = query.strip().rstrip(";")
    # Strip markdown backticks if present
    clean = re.sub(r"^```(?:cypher|sql)?", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"```$", "", clean).strip()

    forbidden = ["DELETE", "DETACH", "DROP", "REMOVE", "SET", "CREATE", "MERGE"]
    upper_tokens = clean.upper().split()
    for f in forbidden:
        if f in upper_tokens:
            raise ValueError(f"Write operation '{f}' is prohibited in read-only Copilot.")
    return clean


def _call_groq(prompt: str, api_key: str) -> Tuple[str, str]:
    """Call Groq API (Meta Llama 3.3 70B)."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "TwinForge-Copilot/1.0",
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        content = res_data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return parsed.get("cypher", ""), parsed.get("explanation", "")


def _call_gemini(prompt: str, api_key: str) -> Tuple[str, str]:
    """Call Google Gemini 2.0 Flash / 1.5 Flash."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        return parsed.get("cypher", ""), parsed.get("explanation", "")


def _semantic_engine_fallback(question: str) -> Tuple[str, str]:
    """Intelligent zero-key intent & entity matcher compiling NL to Cypher."""
    q = question.lower().strip()

    # Match Machine ID (e.g. M7, M12, M1)
    m_match = re.search(r"\b(m\d{1,2})\b", q, re.IGNORECASE)
    machine_id = m_match.group(1).upper() if m_match else None

    # Match Product ID (e.g. P4, P12)
    p_match = re.search(r"\b(p\d{1,2})\b", q, re.IGNORECASE)
    product_id = p_match.group(1).upper() if p_match else None

    # Match Part ID (e.g. PT-4, PART_...)
    part_match = re.search(r"\b(pt-?\d{1,2}|part[_\w]+)\b", q, re.IGNORECASE)
    part_id = part_match.group(1).upper() if part_match else None

    # 1. At-Risk / Failing Machines
    if any(k in q for k in ["risk", "fail", "breakdown", "health", "vibrat", "temp"]):
        if machine_id:
            return (
                f"MATCH (m:Machine {{id: '{machine_id}'}}) "
                f"RETURN m.id AS id, m.name AS name, m.failure_risk AS risk, "
                f"m.predicted_failure_days AS days_to_failure",
                f"Inspect predictive health telemetry and failure risk for Machine {machine_id}."
            )
        threshold = 0.70
        if "80" in q or "0.8" in q:
            threshold = 0.80
        elif "90" in q or "0.9" in q:
            threshold = 0.90
        return (
            f"MATCH (m:Machine) WHERE m.failure_risk >= {threshold} "
            f"RETURN m.id AS id, m.name AS name, m.failure_risk AS risk, "
            f"m.predicted_failure_days AS days_to_failure "
            f"ORDER BY m.failure_risk DESC",
            f"Identifies all assets with failure risk exceeding {int(threshold*100)}%."
        )

    # 2. Downstream Blast Radius & Machine Dependencies
    if machine_id or any(k in q for k in ["impact", "downstream", "blast", "affect", "depend"]):
        target = machine_id or "M7"
        return (
            f"MATCH (m:Machine {{id: '{target}'}})-[:PRODUCES]->(p:Part)-[:USED_IN]->(prod:Product)"
            f"-[:STOCKED_AT]->(w:Warehouse)-[:SERVES]->(c:Customer) "
            f"RETURN p.name AS part, prod.id AS product_id, prod.name AS product_name, "
            f"w.name AS warehouse, count(DISTINCT c) AS customers_affected LIMIT 25",
            f"Traverse 5 hops from Machine {target} to discover downstream parts, products, warehouses, and customer SLA exposure."
        )

    # 3. Inventory Shortfall / Warehouse Gaps
    if any(k in q for k in ["shortfall", "inventory", "stock", "warehouse", "buffer", "demand"]):
        if product_id:
            return (
                f"MATCH (p:Product {{id: '{product_id}'}})-[s:STOCKED_AT]->(w:Warehouse) "
                f"RETURN p.id AS product, p.name AS name, p.forecast_30d AS forecast_demand, "
                f"sum(s.qty) AS total_stock, (p.forecast_30d - sum(s.qty)) AS shortfall",
                f"Calculate projected 30-day inventory shortfall for product {product_id} across regional warehouses."
            )
        return (
            "MATCH (p:Product)-[s:STOCKED_AT]->(w:Warehouse) "
            "WITH p, sum(s.qty) AS total_stock "
            "WHERE (p.forecast_30d - total_stock) > 0 "
            "RETURN p.id AS product_id, p.name AS product_name, p.forecast_30d AS demand, "
            "total_stock, (p.forecast_30d - total_stock) AS shortfall "
            "ORDER BY shortfall DESC LIMIT 10",
            "Identifies products where projected 30-day demand exceeds warehouse buffer stock."
        )

    # 4. Single Points of Failure (SPOF)
    if any(k in q for k in ["spof", "single point", "bottleneck", "sole", "redundanc"]):
        return (
            "MATCH (p:Part) WHERE p.single_point_of_failure = true "
            "OPTIONAL MATCH (m:Machine)-[:PRODUCES]->(p) "
            "RETURN p.id AS part_id, p.name AS part_name, collect(m.id) AS producing_machines "
            "LIMIT 15",
            "Scans supply chain topology for components lacking redundant manufacturing machines or secondary suppliers."
        )

    # 5. Alternate Suppliers & Lead Times
    if any(k in q for k in ["supplier", "alternate", "vendor", "lead time", "backup"]):
        target_part = part_id or "PART_M7_ROTOR"
        if target_part in ["PT-4", "PT4", "ROTOR", "PT"]:
            target_part = "PART_M7_ROTOR"
        return (
            f"MATCH (p:Part)<-[s:SUPPLIES]-(sup:Supplier) "
            f"WHERE p.id = '{target_part}' OR p.id CONTAINS '{target_part}' OR toLower(p.name) CONTAINS 'rotor' "
            f"OPTIONAL MATCH (sup)-[:ALTERNATE_FOR]->(alt:Supplier) "
            f"RETURN p.name AS part, sup.name AS primary_supplier, s.lead_time_days AS lead_time, "
            f"collect(alt.name) AS backup_suppliers LIMIT 5",
            f"Find primary and emergency substitute suppliers for component {target_part} ranked by delivery lead time."
        )

    # 6. Decisions & Governance Audit Trail
    if any(k in q for k in ["decision", "audit", "action", "reroute", "schedule", "evidence", "lineage"]):
        return (
            "MATCH (d:Decision)-[r:BASED_ON]->(evidence) "
            "RETURN d.id AS decision_id, d.type AS action_type, d.target AS target_asset, "
            "d.reason AS justification, count(evidence) AS supporting_evidence_count "
            "ORDER BY d.id DESC LIMIT 10",
            "Retrieves audited operational decisions committed into FalkorDB with grounded [:BASED_ON] evidence lineage."
        )

    # 7. Plants and Facilities
    if any(k in q for k in ["plant", "factory", "facility", "leipzig", "austin", "tokyo", "munich"]):
        return (
            "MATCH (pl:Plant)-[:HAS]->(m:Machine) "
            "RETURN pl.id AS plant_id, pl.name AS plant_name, count(m) AS machine_count, "
            "avg(m.failure_risk) AS average_risk "
            "ORDER BY average_risk DESC",
            "Summarizes operational capacity and fleet risk distribution across all manufacturing facilities."
        )

    # Default: General Graph Inspection
    return (
        "MATCH (m:Machine) RETURN m.id AS id, m.name AS name, m.failure_risk AS risk, "
        "m.predicted_failure_days AS days_left ORDER BY m.failure_risk DESC LIMIT 10",
        "General graph query inspecting top physical shopfloor assets and real-time failure probabilities."
    )


def _synthesize_answer(question: str, cypher: str, results: List[List[Any]], columns: List[str]) -> str:
    """Produces a clean, human-readable answer grounded in the graph query results."""
    if not results:
        return f"Query returned 0 records. The FalkorDB graph contains no matching nodes or edges for this criteria."

    row_count = len(results)
    col_map = {col.lower(): idx for idx, col in enumerate(columns)}

    # Machine / Risk formatting
    if "risk" in col_map and "id" in col_map:
        lines = []
        for row in results[:5]:
            m_id = row[col_map["id"]]
            risk = row[col_map["risk"]]
            days_idx = col_map.get("days_to_failure") or col_map.get("days_left")
            days = row[days_idx] if days_idx is not None else "?"
            risk_pct = int(round(risk * 100)) if isinstance(risk, (int, float)) else risk
            lines.append(f"• **Machine {m_id}**: Failure Risk {risk_pct}% (Predicted Breakdown in {days} days)")
        return (
            f"FalkorDB identified **{row_count} assets** matching your query:\n\n"
            + "\n".join(lines)
            + ("\n\n*(Showing top 5 assets)*" if row_count > 5 else "")
        )

    # Shortfall formatting
    if "shortfall" in col_map:
        lines = []
        for row in results[:5]:
            p_id = row[col_map.get("product_id") or col_map.get("product")]
            p_name = row[col_map.get("product_name") or col_map.get("name")]
            sf = row[col_map["shortfall"]]
            lines.append(f"• **{p_name} ({p_id})**: Projected deficit of **{int(sf):,} units**")
        return (
            f"Identified **{row_count} products** with inventory deficits across warehouse buffers:\n\n"
            + "\n".join(lines)
        )

    # Decision formatting
    if "decision_id" in col_map:
        lines = []
        for row in results[:4]:
            d_id = row[col_map["decision_id"]]
            action = row[col_map["action_type"]]
            target = row[col_map["target_asset"]]
            reason = row[col_map["justification"]]
            lines.append(f"• **{d_id}** (`{action}` on {target}): {reason}")
        return f"Found **{row_count} audited decision records** in the graph:\n\n" + "\n".join(lines)

    # Supplier formatting
    if "primary_supplier" in col_map:
        lines = []
        for row in results[:5]:
            p_name = row[col_map.get("part", 0)]
            sup = row[col_map["primary_supplier"]]
            lt_idx = col_map.get("lead_time")
            lt = row[lt_idx] if lt_idx is not None else "Standard"
            alt_idx = col_map.get("backup_suppliers")
            alts = row[alt_idx] if alt_idx is not None else []
            alt_str = f" *(Alternates: {', '.join(alts)})*" if alts else ""
            lines.append(f"• **{p_name}**: Primary Supplier `{sup}` ({lt} days lead time){alt_str}")
        return f"Found **{row_count} supplier relationship(s)** in the graph:\n\n" + "\n".join(lines)

    # Generic Table Summary
    preview = []
    for r in results[:4]:
        pairs = [f"{columns[i]}: {r[i]}" for i in range(min(4, len(columns)))]
        preview.append("• " + ", ".join(pairs))
    return f"FalkorDB returned **{row_count} records** in response to your query:\n\n" + "\n".join(preview)


def ask_copilot(question: str) -> Dict[str, Any]:
    """Top-level entrypoint for Natural Language Graph Copilot.
    Auto-detects active provider: Groq (Llama 3.3) -> Gemini (2.0 Flash) -> Built-in Engine.
    """
    start_time = time.perf_counter()
    question = question.strip()
    if not question:
        return {"status": "error", "message": "Please enter a question."}

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()

    provider = "TwinForge Semantic Engine (Zero-Key Built-in)"
    model_name = "Rule-Grounded Graph Parser"
    cypher_query = ""
    explanation = ""

    # 1. Try Groq (Llama 3.3 70B)
    if groq_key:
        try:
            cypher_query, explanation = _call_groq(question, groq_key)
            provider = "Groq"
            model_name = "Meta Llama 3.3 70B"
        except Exception as e:
            print(f"[Copilot Warning] Groq call failed: {e}. Falling back...")

    # 2. Try Gemini 2.0 Flash
    if not cypher_query and gemini_key:
        try:
            cypher_query, explanation = _call_gemini(question, gemini_key)
            provider = "Google AI Studio"
            model_name = "Gemini 2.0 Flash"
        except Exception as e:
            print(f"[Copilot Warning] Gemini call failed: {e}. Falling back...")

    # 3. Built-in Fallback (Always Works!)
    if not cypher_query:
        cypher_query, explanation = _semantic_engine_fallback(question)
        provider = "TwinForge Semantic Engine"
        model_name = "Built-in Graph Parser (100% Free)"

    # Clean and execute on FalkorDB
    try:
        clean_query = _clean_cypher(cypher_query)
        g = get_graph()
        
        t0 = time.perf_counter()
        query_res = g.query(clean_query)
        falkor_latency = round((time.perf_counter() - t0) * 1000, 2)
        
        results = query_res.result_set or []
        columns = [
            str(col[1]) if isinstance(col, (list, tuple)) and len(col) > 1 else str(col)
            for col in (getattr(query_res, "header", []) or [])
        ]
        if not columns and results:
            columns = [f"col_{i+1}" for i in range(len(results[0]))]

        total_latency = round((time.perf_counter() - start_time) * 1000, 1)
        answer = _synthesize_answer(question, clean_query, results, columns)

        return {
            "status": "success",
            "provider": provider,
            "model": model_name,
            "question": question,
            "cypher": clean_query,
            "explanation": explanation,
            "answer": answer,
            "row_count": len(results),
            "falkordb_latency_ms": falkor_latency,
            "total_latency_ms": total_latency,
            "columns": columns,
            "results": results[:15],  # Return up to 15 rows for inspection
        }
    except Exception as e:
        return {
            "status": "error",
            "provider": provider,
            "model": model_name,
            "question": question,
            "cypher": cypher_query,
            "error": str(e),
            "falkordb_latency_ms": 0.0,
        }
