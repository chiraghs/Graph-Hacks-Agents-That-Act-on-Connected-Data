"""service.py - Multi-Provider Natural Language to Cypher Graph Copilot with Multi-Query Decomposition.

Supports:
1. Groq (Meta Llama 3.3 70B / OpenAI OSS) via `GROQ_API_KEY` (Free, 500 t/s)
2. Google Gemini (Gemini 2.0 Flash / 1.5 Flash) via `GEMINI_API_KEY` or `GOOGLE_API_KEY` (Free tier)
3. TwinForge Built-in Semantic Graph Engine (Zero-Key Fallback, always available, <5ms)
4. Multi-Question / Compound Query Decomposition & Batch Graph Execution
"""

import os
import re
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Tuple, Optional
from core.db import get_graph

# Cypher Knowledge Graph Schema Context
GRAPH_SCHEMA = """
FalkorDB Property Graph Schema:
Graph Name: supply_chain (175 nodes, 465 relationships)

Node Labels & Properties:
- Plant: {id (e.g. PLANT_DETROIT, PLANT_MUNICH, PLANT_AUSTIN), name, location}
- Machine: {id (e.g. M1 to M25, M7, M12), name, failure_risk (0.0-1.0), predicted_failure_days (int)}
- Part: {id (e.g. PART_54, PART_M7_ROTOR, PART_SPOF_ALLOY), name, cost}
- Product: {id (e.g. P4, P12, P1 to P20), name, forecast_30d, safety_stock}
- Warehouse: {id (e.g. WH_MIDWEST, WH_NORDIC), name, location, capacity}
- Customer: {id (e.g. CUST_001 to CUST_040), name, tier (Strategic, Enterprise, Standard)}
- Supplier: {id (e.g. SUPPLIER_01 to SUPPLIER_13, SUPPLIER_ALT_M7, SUPPLIER_SOLO_SPOF), name, rating}
- Region: {id (e.g. REG_NA, REG_EU, REG_EAST_ASIA, REG_SE_ASIA, REG_LATAM), name}

Relationship Types:
- (:Plant)-[:HAS]->(:Machine)
- (:Machine)-[:PRODUCES]->(:Part)
- (:Supplier)-[:SUPPLIES]->(:Part)
- (:Supplier)-[:LOCATED_IN]->(:Region)
- (:Supplier)-[:ALTERNATE_FOR]->(:Supplier)
- (:Part)-[:USED_IN]->(:Product)
- (:Product)-[:STOCKED_AT {qty}]->(:Warehouse)
- (:Warehouse)-[:SERVES]->(:Customer)

Domain Logic Notes:
- Health score below 75 translates to failure_risk > 0.25 (e.g. M7 at 0.94, M12 at 0.88).
- Machine telemetry alerts or anomalies correspond to high failure_risk (> 0.70) or imminent predicted_failure_days (< 10).
- Inventory deficit or shortfall is calculated as (p.forecast_30d - sum(s.qty)) across STOCKED_AT relationships.
"""

SYSTEM_PROMPT = f"""You are the TwinForge Graph Copilot, an expert industrial AI assistant connected to a FalkorDB graph database.
Given a user's question, produce read-only Cypher queries and concise natural language explanations.

{GRAPH_SCHEMA}

RULES:
1. ONLY write read-only Cypher queries (MATCH, WHERE, RETURN, ORDER BY, LIMIT). Never write CREATE, DELETE, SET, MERGE, or DROP.
2. If the user asks a SINGLE question, return a strict JSON object:
   {{
     "mode": "single",
     "cypher": "<valid Cypher query>",
     "explanation": "<brief summary of what this query discovers in the supply chain>"
   }}
3. If the user asks MULTIPLE questions or compound requests (e.g., asking about machines AND suppliers AND parts AND sensor anomalies, or multiple questions in quotes or numbers), decompose them into an array of sub-queries:
   {{
     "mode": "multi",
     "queries": [
       {{
         "topic": "<short 2-4 word title, e.g. Machine Health, Supplier Network, Low Stock Inventory, Sensor Alerts>",
         "question": "<the specific sub-question being answered>",
         "cypher": "<valid Cypher query for this sub-question>",
         "explanation": "<brief summary>"
       }}
     ]
   }}
4. Keep queries focused and use LIMIT 25 unless counting.
5. Do not include markdown code fences (like ```json), just output raw JSON.
"""


def _clean_cypher(query: str) -> str:
    """Sanitizes and enforces read-only safety on Cypher queries."""
    clean = query.strip().rstrip(";")
    clean = re.sub(r"^```(?:cypher|sql)?", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"```$", "", clean).strip()

    forbidden = ["DELETE", "DETACH", "DROP", "REMOVE", "SET", "CREATE", "MERGE"]
    upper_tokens = clean.upper().split()
    for f in forbidden:
        if f in upper_tokens:
            raise ValueError(f"Write operation '{f}' is prohibited in read-only Copilot.")
    return clean


def _call_groq(prompt: str, api_key: str) -> Dict[str, Any]:
    """Call Groq API using available high-performance models."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; TwinForge/1.0)",
    }

    models_to_try = ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]
    last_err = None

    for model in models_to_try:
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=12) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                content = res_data["choices"][0]["message"]["content"]
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    return parsed
                return {"mode": "single", "cypher": "", "explanation": content}
        except Exception as e:
            last_err = e
            continue

    if last_err:
        raise last_err
    return {}


def _call_gemini(prompt: str, api_key: str) -> Dict[str, Any]:
    """Call Google Gemini 2.0 Flash / 1.5 Flash."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=12) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            return parsed
        return {"mode": "single", "cypher": "", "explanation": text}


def _semantic_engine_single(question: str) -> Tuple[str, str]:
    """Pattern-matcher for a single user question compiling NL to Cypher."""
    q = question.lower().strip()

    # Match Machine ID
    m_match = re.search(r"\b(m\d{1,2})\b", q, re.IGNORECASE)
    machine_id = m_match.group(1).upper() if m_match else None

    # Match Product ID
    p_match = re.search(r"\b(p\d{1,2})\b", q, re.IGNORECASE)
    product_id = p_match.group(1).upper() if p_match else None

    # Match Part ID
    part_match = re.search(r"\b(pt-?\d{1,2}|part[_\w]+)\b", q, re.IGNORECASE)
    part_id = part_match.group(1).upper() if part_match else None

    # 1. At-Risk / Failing Machines / Health
    if any(k in q for k in ["risk", "fail", "breakdown", "health", "vibrat", "temp"]):
        if machine_id:
            return (
                f"MATCH (m:Machine {{id: '{machine_id}'}}) "
                f"RETURN m.id AS machine_id, m.name AS machine_name, m.failure_risk AS failure_risk, "
                f"m.predicted_failure_days AS predicted_failure_days",
                f"Inspect predictive health telemetry and failure risk for Machine {machine_id}."
            )
        threshold = 0.25 if ("75" in q or "health" in q) else 0.70
        return (
            f"MATCH (m:Machine) WHERE m.failure_risk >= {threshold} "
            f"RETURN m.id AS machine_id, m.name AS machine_name, m.failure_risk AS failure_risk, "
            f"m.predicted_failure_days AS predicted_failure_days "
            f"ORDER BY m.failure_risk DESC LIMIT 25",
            f"Identifies physical assets with failure risk exceeding {int(threshold*100)}% (health score below {100-int(threshold*100)})."
        )

    # 2. Sensor Alerts & Anomalies
    if any(k in q for k in ["alert", "anomal", "sensor", "telemetry"]):
        return (
            "MATCH (m:Machine) WHERE m.failure_risk >= 0.70 OR m.predicted_failure_days <= 10 "
            "RETURN m.id AS machine_id, m.name AS machine_name, m.failure_risk AS failure_risk, "
            "m.predicted_failure_days AS breakdown_imminent_days "
            "ORDER BY m.failure_risk DESC LIMIT 15",
            "Scans connected shopfloor telemetry for critical vibration anomalies and imminent machine breakdowns."
        )

    # 3. Suppliers & Location / Risk Rating
    if any(k in q for k in ["supplier", "vendor", "alternate", "lead time"]):
        return (
            "MATCH (s:Supplier)-[:LOCATED_IN]->(r:Region) "
            "RETURN s.id AS supplier_id, s.name AS supplier_name, r.name AS location, s.rating AS quality_rating "
            "ORDER BY s.rating DESC LIMIT 25",
            "Retrieves all active suppliers, their operating geographic regions, and benchmark quality ratings."
        )

    # 4. Inventory Shortfall / Stock Gaps
    if any(k in q for k in ["shortfall", "inventory", "stock", "warehouse", "buffer", "deficit"]):
        if product_id:
            return (
                f"MATCH (p:Product {{id: '{product_id}'}})-[s:STOCKED_AT]->(w:Warehouse) "
                f"RETURN p.id AS product, p.name AS name, p.forecast_30d AS forecast_demand, "
                f"sum(s.qty) AS total_stock, (p.forecast_30d - sum(s.qty)) AS shortfall",
                f"Calculate projected 30-day inventory shortfall for product {product_id}."
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

    # 5. Downstream Impact
    if machine_id or any(k in q for k in ["impact", "downstream", "blast", "affect", "depend"]):
        target = machine_id or "M7"
        return (
            f"MATCH (m:Machine {{id: '{target}'}})-[:PRODUCES]->(p:Part)-[:USED_IN]->(prod:Product)"
            f"-[:STOCKED_AT]->(w:Warehouse)-[:SERVES]->(c:Customer) "
            f"RETURN p.name AS part, prod.id AS product_id, prod.name AS product_name, "
            f"w.name AS warehouse, count(DISTINCT c) AS customers_affected LIMIT 25",
            f"Traverse 5 hops from Machine {target} to discover downstream parts, products, warehouses, and customer SLA exposure."
        )

    # 6. Plants and Facilities
    if any(k in q for k in ["plant", "factory", "facility", "detroit", "austin", "munich"]):
        return (
            "MATCH (pl:Plant)-[:HAS]->(m:Machine) "
            "RETURN pl.id AS plant_id, pl.name AS plant_name, pl.location AS location, count(m) AS machine_count "
            "ORDER BY pl.name",
            "Summarizes operational capacity and fleet machine count across all manufacturing facilities."
        )

    # Default
    return (
        "MATCH (m:Machine) RETURN m.id AS machine_id, m.name AS machine_name, m.failure_risk AS failure_risk, "
        "m.predicted_failure_days AS predicted_failure_days ORDER BY m.failure_risk DESC LIMIT 10",
        "General graph query inspecting top physical shopfloor assets and real-time failure probabilities."
    )


def _semantic_engine_fallback(question: str) -> Dict[str, Any]:
    """Detects multi-question inputs in the zero-key fallback parser."""
    # Check for multiple quoted questions: "q1" "q2" "q3"
    quoted = re.findall(r"\"([^\"]{5,})\"", question)
    if len(quoted) >= 2:
        queries = []
        for idx, q_text in enumerate(quoted):
            cypher, expl = _semantic_engine_single(q_text)
            topic = "Query " + str(idx + 1)
            q_lower = q_text.lower()
            if "machine" in q_lower or "health" in q_lower:
                topic = "Machine Health"
            elif "supplier" in q_lower:
                topic = "Supplier Network"
            elif "stock" in q_lower or "part" in q_lower or "inventory" in q_lower:
                topic = "Stock & Inventory"
            elif "alert" in q_lower or "sensor" in q_lower or "anomal" in q_lower:
                topic = "Sensor Alerts"
            queries.append({
                "topic": topic,
                "question": q_text,
                "cypher": cypher,
                "explanation": expl,
            })
        return {"mode": "multi", "queries": queries}

    # Check for numbered questions: 1. ... 2. ...
    numbered = re.split(r"\n?\s*\d+\.\s+", question)
    numbered = [item.strip() for item in numbered if len(item.strip()) > 5]
    if len(numbered) >= 2:
        queries = []
        for idx, q_text in enumerate(numbered):
            cypher, expl = _semantic_engine_single(q_text)
            queries.append({
                "topic": f"Item {idx + 1}",
                "question": q_text,
                "cypher": cypher,
                "explanation": expl,
            })
        return {"mode": "multi", "queries": queries}

    cypher, expl = _semantic_engine_single(question)
    return {"mode": "single", "cypher": cypher, "explanation": expl}


def _synthesize_answer(question: str, cypher: str, results: List[List[Any]], columns: List[str]) -> str:
    """Produces clean, human-readable answers grounded in graph query results."""
    if not results:
        return "Query returned **0 records**. No matching entities or thresholds found in the graph."

    row_count = len(results)
    col_map = {col.lower(): idx for idx, col in enumerate(columns)}

    # Machine / Risk formatting
    if any(k in col_map for k in ["failure_risk", "risk"]):
        risk_idx = col_map.get("failure_risk", col_map.get("risk"))
        name_idx = col_map.get("machine_name", col_map.get("name", col_map.get("machine_id", col_map.get("id"))))
        days_idx = col_map.get("predicted_failure_days", col_map.get("breakdown_imminent_days"))
        lines = []
        for row in results[:6]:
            name = row[name_idx] if name_idx is not None else "Machine"
            risk = row[risk_idx]
            risk_pct = int(round(risk * 100)) if isinstance(risk, (int, float)) else risk
            days_str = f" — Predicted breakdown in **{row[days_idx]} days**" if (days_idx is not None and row[days_idx] is not None) else ""
            lines.append(f"• **{name}**: Failure Risk **{risk_pct}%**{days_str}")
        return f"Found **{row_count} assets** matching risk criteria:\n\n" + "\n".join(lines)

    # Supplier formatting
    if any(k in col_map for k in ["supplier_name", "supplier_id"]):
        name_idx = col_map.get("supplier_name", col_map.get("name", 0))
        loc_idx = col_map.get("location", col_map.get("region_name"))
        rate_idx = col_map.get("quality_rating", col_map.get("rating", col_map.get("risk_rating")))
        lines = []
        for row in results[:6]:
            name = row[name_idx]
            loc_str = f" ({row[loc_idx]})" if loc_idx is not None and row[loc_idx] else ""
            rate_str = f" — Rating: **{row[rate_idx]} / 5.0**" if rate_idx is not None and row[rate_idx] else ""
            lines.append(f"• **{name}**{loc_str}{rate_str}")
        return f"Found **{row_count} active suppliers** in network:\n\n" + "\n".join(lines)

    # Shortfall / Inventory formatting
    if "shortfall" in col_map:
        lines = []
        for row in results[:5]:
            p_name = row[col_map.get("product_name", col_map.get("name", 0))]
            sf = row[col_map["shortfall"]]
            lines.append(f"• **{p_name}**: Projected deficit of **{int(sf):,} units**")
        return f"Identified **{row_count} products** with inventory buffer deficits:\n\n" + "\n".join(lines)

    # Plant formatting
    if any(k in col_map for k in ["plant_name", "plant_id"]):
        name_idx = col_map.get("plant_name", col_map.get("name", 0))
        loc_idx = col_map.get("location")
        m_cnt_idx = col_map.get("machine_count")
        lines = []
        for row in results[:5]:
            name = row[name_idx]
            loc_str = f" in {row[loc_idx]}" if loc_idx is not None and row[loc_idx] else ""
            cnt_str = f" — **{row[m_cnt_idx]} machines**" if m_cnt_idx is not None else ""
            lines.append(f"• **{name}**{loc_str}{cnt_str}")
        return f"Found **{row_count} manufacturing plants**:\n\n" + "\n".join(lines)

    # Generic Table Summary
    preview = []
    for r in results[:4]:
        pairs = [f"{columns[i]}: {r[i]}" for i in range(min(4, len(columns)))]
        preview.append("• " + ", ".join(pairs))
    return f"FalkorDB returned **{row_count} records**:\n\n" + "\n".join(preview)


def ask_copilot(question: str) -> Dict[str, Any]:
    """Top-level entrypoint for Natural Language Graph Copilot.
    Supports single queries and compound/multi-question decomposition with batch execution.
    """
    start_time = time.perf_counter()
    question = question.strip()
    if not question:
        return {"status": "error", "message": "Please enter a question."}

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()

    provider = "TwinForge Semantic Engine (Zero-Key Built-in)"
    model_name = "Rule-Grounded Graph Parser"
    llm_payload: Dict[str, Any] = {}

    # 1. Try Groq (Llama 3.3 70B / OpenAI OSS)
    if groq_key:
        try:
            llm_payload = _call_groq(question, groq_key)
            provider = "Groq"
            model_name = "Meta Llama 3.3 70B"
        except Exception as e:
            print(f"[Copilot Warning] Groq call failed: {e}. Falling back...")

    # 2. Try Gemini 2.0 Flash
    if not llm_payload.get("cypher") and not llm_payload.get("queries") and gemini_key:
        try:
            llm_payload = _call_gemini(question, gemini_key)
            provider = "Google AI Studio"
            model_name = "Gemini 2.0 Flash"
        except Exception as e:
            print(f"[Copilot Warning] Gemini call failed: {e}. Falling back...")

    # 3. Built-in Fallback
    if not llm_payload.get("cypher") and not llm_payload.get("queries"):
        llm_payload = _semantic_engine_fallback(question)
        provider = "TwinForge Semantic Engine"
        model_name = "Built-in Graph Parser (100% Free)"

    is_multi = llm_payload.get("mode") == "multi" or (isinstance(llm_payload.get("queries"), list) and len(llm_payload["queries"]) > 1)

    # ==========================================
    # MULTI-QUERY EXECUTION PIPELINE
    # ==========================================
    if is_multi:
        sub_queries = llm_payload.get("queries", [])
        g = get_graph()
        executed_sub_queries = []
        total_falkor_latency = 0.0
        report_sections = []
        combined_cyphers = []

        for idx, sq in enumerate(sub_queries):
            topic = sq.get("topic", f"Section {idx + 1}")
            sub_q = sq.get("question", "")
            raw_cypher = sq.get("cypher", "")
            explanation = sq.get("explanation", "")

            try:
                clean_cypher = _clean_cypher(raw_cypher)
                t0 = time.perf_counter()
                query_res = g.query(clean_cypher)
                falkor_lat = round((time.perf_counter() - t0) * 1000, 2)
                total_falkor_latency += falkor_lat

                results = query_res.result_set or []
                columns = [
                    str(col[1]) if isinstance(col, (list, tuple)) and len(col) > 1 else str(col)
                    for col in (getattr(query_res, "header", []) or [])
                ]
                if not columns and results:
                    columns = [f"col_{i+1}" for i in range(len(results[0]))]

                sub_ans = _synthesize_answer(sub_q, clean_cypher, results, columns)
                executed_sub_queries.append({
                    "topic": topic,
                    "question": sub_q,
                    "cypher": clean_cypher,
                    "explanation": explanation,
                    "answer": sub_ans,
                    "row_count": len(results),
                    "falkordb_latency_ms": falkor_lat,
                    "columns": columns,
                    "results": results[:10],
                })
                combined_cyphers.append(f"// --- {topic} ---\n{clean_cypher}")

                # Build section for markdown answer
                report_sections.append(f"### {idx + 1}. {topic}\n*{explanation}*\n\n{sub_ans}")

            except Exception as query_err:
                executed_sub_queries.append({
                    "topic": topic,
                    "question": sub_q,
                    "cypher": raw_cypher,
                    "error": str(query_err),
                    "answer": f"⚠️ Could not execute query: {query_err}",
                    "row_count": 0,
                    "falkordb_latency_ms": 0.0,
                })
                report_sections.append(f"### {idx + 1}. {topic}\n⚠️ *Query error*: {query_err}")

        total_latency = round((time.perf_counter() - start_time) * 1000, 1)
        total_rows = sum(item.get("row_count", 0) for item in executed_sub_queries)

        combined_answer = (
            f"FalkorDB decomposed your request into **{len(executed_sub_queries)} targeted graph queries** "
            f"and analyzed the results across the network:\n\n"
            + "\n\n".join(report_sections)
        )

        return {
            "status": "success",
            "mode": "multi",
            "provider": provider,
            "model": model_name,
            "question": question,
            "cypher": "\n\n".join(combined_cyphers),
            "explanation": f"Decomposed compound inquiry into {len(executed_sub_queries)} parallel Cypher operations.",
            "answer": combined_answer,
            "row_count": total_rows,
            "falkordb_latency_ms": round(total_falkor_latency, 2),
            "total_latency_ms": total_latency,
            "queries": executed_sub_queries,
            "columns": executed_sub_queries[0]["columns"] if executed_sub_queries and "columns" in executed_sub_queries[0] else [],
            "results": executed_sub_queries[0]["results"] if executed_sub_queries and "results" in executed_sub_queries[0] else [],
        }

    # ==========================================
    # SINGLE QUERY EXECUTION PIPELINE
    # ==========================================
    cypher_query = llm_payload.get("cypher", "")
    explanation = llm_payload.get("explanation", "")

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
            "mode": "single",
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
            "results": results[:15],
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
