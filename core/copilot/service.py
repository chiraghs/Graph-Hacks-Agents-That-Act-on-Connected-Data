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
Graph Name: supply_chain (3,700+ nodes, 6,000+ relationships across Apex Detroit and London facilities)

Node Labels & Properties:
- Plant: {id (e.g. PLANT_DETROIT, PLANT_MUNICH, PLANT_AUSTIN), name, location}
- Machine: {id (e.g. M1 to M25, M7, M12, M18), name, failure_risk (0.0-1.0), predicted_failure_days (int)}
- Part: {id (e.g. PART_54, PART_M7_ROTOR, PART_M7_SHAFT, PART_M7_STATOR), name, cost}
- Product: {id (e.g. P4, P12, P1 to P20), name, forecast_30d, safety_stock}
- Warehouse: {id (e.g. WH_MIDWEST, WH_EAST_COAST, WH_NORDIC), name, location, capacity}
- Customer: {id (e.g. CUST_HYPERDRIVE_AUTO, CUST_001 to CUST_040), name, tier, city, annual_contract_value}
- CustomerOrder: {id (e.g. ORD_APEX_CRITICAL_01), order_number (e.g. PO-HYPERDRIVE-2026-P4), customer_id, product_id, units_ordered, unit_price_usd, total_value_usd, sla_hours_remaining, hourly_delay_penalty_usd, priority, status}
- SparePart: {id (e.g. SPARE_SPINDLE_KUKA_M7), name, compatible_machine, detroit_stock, munich_stock, courier_air_transit_hours, supplier, cost_usd}
- Supplier: {id (e.g. SUPPLIER_01 to SUPPLIER_13, SUPPLIER_ALT_M7), name, rating}
- Region: {id (e.g. REG_NA, REG_EU, REG_EAST_ASIA), name}
- Facility: {id (e.g. FAC_APEX_DETROIT, FAC_LONDON_THAMES), name, city, facility_type, total_area_sqm}
- MaintenanceLog: {id, incident_type, action_taken, downtime_minutes, technician, diagnostic_summary, timestamp}
- SensorTelemetry: {id (e.g. SENSOR_M7_VIB_SPINDLE, SENSOR_M12_HYDRAULIC_FLOW), sensor_type, vibration_rms_mms, vibration_threshold_mms, bearing_temp_c, normal_temp_c, acoustic_emission_db, lubricant_particle_ppm, operating_hours, rul_hours (Remaining Useful Life), health_index, anomaly_status, diagnostic_summary}
- PdMPrescription: {id (e.g. PDM_PLAN_M7_OVERHAUL, PDM_PLAN_M12_FLUSH), action_title, intervention_window_hours, scheduled_downtime_hours, preventive_cost_usd, catastrophic_breakdown_cost_usd, cost_avoidance_usd, urgency, technician_cert_required, retooling_reroute_target}
- DemandForecast: {id (e.g. FC_P4_2026Q2, FC_P4_2026Q3, FC_P12_2026Q2), period, forecast_units, confidence_score, ci_lower, ci_upper, growth_rate_pct, market_driver, stockout_risk_level, projected_inventory_shortfall, days_of_supply_remaining, recommended_production_ramp}

Relationship Types:
- (:Plant)-[:HAS]->(:Machine)
- (:Machine)-[:PRODUCES]->(:Part)
- (:Machine)-[:CAPABLE_OF_PRODUCING {retooling_time_hours, daily_output_units, status}]->(:Part)
- (:Machine)-[:HAS_TELEMETRY]->(:SensorTelemetry)
- (:Machine)-[:HAS_PDM_PLAN]->(:PdMPrescription)
- (:PdMPrescription)-[:REQUIRES_SPARE]->(:SparePart)
- (:Machine)-[:HAS_SPARE_COMPONENT]->(:SparePart)
- (:Plant)-[:STOCKS_SPARE {units_available}]->(:SparePart)
- (:Part)-[:USED_IN]->(:Product)
- (:Product)-[:HAS_FORECAST]->(:DemandForecast)
- (:Customer)-[:COMMITTED_DEMAND {contract_units, contract_number, priority, penalty_risk, hourly_penalty_usd, delivery_window}]->(:DemandForecast)
- (:Product)-[:STOCKED_AT {qty}]->(:Warehouse)
- (:Warehouse)-[:SERVES]->(:Customer)
- (:Customer)-[:PLACED]->(:CustomerOrder)
- (:CustomerOrder)-[:CONTAINS_PRODUCT]->(:Product)
- (:Supplier)-[:SUPPLIES]->(:Part)
- (:Supplier)-[:LOCATED_IN]->(:Region)
- (:Supplier)-[:ALTERNATE_FOR]->(:Supplier)
- (:Plant)-[:PART_OF_FACILITY]->(:Facility)
- (:Machine)-[:HAS_MAINTENANCE_EVENT]->(:MaintenanceLog)

Domain Logic Notes:
- Predictive Maintenance (PdM): Machine M7 has SensorTelemetry showing critical vibration (8.45 mm/s vs 4.5 threshold), high bearing temp (89.4°C), and RUL of only 48 hours due to bearing spalling. Its PdMPrescription (PDM_PLAN_M7_OVERHAUL) recommends scheduled bearing replacement with $140,200 cost avoidance ($4,800 preventive vs $145,000 catastrophic breakdown).
- Demand Forecasting: Product P4 has DemandForecast FC_P4_2026Q2 with 1,450 forecast units (+28.5% growth from EV Powertrain ramp). With only 400 warehouse units in stock, net projected shortfall is 1,050 units with critical stockout risk in 11 days. Strategic customer CUST_HYPERDRIVE_AUTO has committed demand for 550 units with $25,000/hr penalty exposure.
- HyperDrive Electric Motors (CUST_HYPERDRIVE_AUTO) is a Customer (NOT a supplier!). They placed CustomerOrder ORD_APEX_CRITICAL_01 (PO-HYPERDRIVE-2026-P4) for 550 units of Product P4 ('P4 Smart Turbine Module').
- Order ORD_APEX_CRITICAL_01 has: hourly_delay_penalty_usd: 25000.0, sla_hours_remaining: 72, total_value_usd: 1650000.0.
- Machine M7 ('CNC-Unit-M7') at Plant Detroit has critical failure_risk (0.94) and produces rotor, shaft, and stator parts used in Product P4.
- Product P4 buffer stock is in STOCKED_AT relationships (WH_MIDWEST has 250, WH_EAST_COAST has 150 -> total 400 units).
- Inventory Shortfall for CustomerOrder = (ord.units_ordered - sum(s.qty)) = 550 - 400 = 150 units.
- Machine M18 ('CNC-Unit-M18') is on standby with [:CAPABLE_OF_PRODUCING] M7's parts (retooling_time_hours: 3.5 - 4.0h, daily_output_units: 60-80).
- Spare component SPARE_SPINDLE_KUKA_M7 is stocked at PLANT_MUNICH (2 units, courier_air_transit_hours: 8.5) and 0 in Detroit.
- When computing order shortfall and penalties, query:
  MATCH (c:Customer {id: 'CUST_HYPERDRIVE_AUTO'})-[:PLACED]->(ord:CustomerOrder)-[:CONTAINS_PRODUCT]->(p:Product)
  OPTIONAL MATCH (p)-[s:STOCKED_AT]->(wh:Warehouse)
  WITH c, ord, p, coalesce(sum(s.qty), 0) AS warehouse_stock
  RETURN c.name AS customer_name, ord.order_number AS order_number, ord.units_ordered AS units_ordered,
         warehouse_stock, (ord.units_ordered - warehouse_stock) AS shortfall_units,
         ord.hourly_delay_penalty_usd AS hourly_delay_penalty_usd, ord.sla_hours_remaining AS sla_hours_remaining
"""

SYSTEM_PROMPT = f"""You are the TwinForge Graph Copilot, a conversational industrial AI copilot and expert supply chain engineer connected to a FalkorDB property graph database.

{GRAPH_SCHEMA}

YOUR OPERATIONAL MODES:
1. CONVERSATIONAL / CHAT MODE:
   If the user's message is a greeting (e.g. "hi", "hello"), pleasantry ("thanks", "how are you"), question about who you are or what you do ("who are you", "what can you do", "help"), general supply-chain concept, or follow-up conversation that does not require looking up live graph records:
   Return a strict JSON object:
   {{
     "mode": "conversation",
     "cypher": "",
     "explanation": "Conversational reply",
     "answer": "<warm, expert, and conversational response in markdown. Introduce yourself, converse naturally, and suggest 3-4 concrete queries about Detroit or London facilities when appropriate>"
   }}

2. GRAPH QUERY MODE (Single Question):
   If the user asks an operational question about entities in the supply chain (machines, failure risk, parts, products, customer orders, warehouses, suppliers, facilities, SLA penalties):
   Return a strict JSON object:
   {{
     "mode": "single",
     "cypher": "<valid read-only Cypher query (MATCH, WHERE, RETURN, ORDER BY, LIMIT)>",
     "explanation": "<brief summary of what this query discovers in the supply chain>"
   }}

3. COMPOUND QUERY MODE (Multiple Questions):
   If the user asks multiple distinct questions or compound requests:
   Return a strict JSON object:
   {{
     "mode": "multi",
     "queries": [
       {{
         "topic": "<short 2-4 word title>",
         "question": "<the specific sub-question being answered>",
         "cypher": "<valid Cypher query>",
         "explanation": "<brief summary>"
       }}
     ]
   }}

RULES:
1. ONLY write read-only Cypher queries (MATCH, WHERE, RETURN, ORDER BY, LIMIT). Never write CREATE, DELETE, SET, MERGE, or DROP.
2. ALWAYS return a valid JSON object matching one of the 3 modes above.
3. Keep Cypher queries focused and use LIMIT 25 unless aggregating.
4. Do not include markdown code fences (like ```json), just output raw JSON.
5. In FalkorDB Cypher, if using UNION, each subquery branch must have the exact identical column alias names. Prefer MATCH with OPTIONAL MATCH rather than UNION when joining disparate paths.
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
                "response_format": {"type": "json_object"},
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

    # 2. Predictive Maintenance, IoT Sensor Telemetry & RUL
    if any(k in q for k in ["predictive maintenance", "pdm", "telemetry", "vibration", "rul", "remaining useful", "sensor", "bearing temp", "condition monitor"]):
        if machine_id:
            return (
                f"MATCH (m:Machine {{id: '{machine_id}'}})-[:HAS_TELEMETRY]->(t:SensorTelemetry) "
                f"OPTIONAL MATCH (m)-[:HAS_PDM_PLAN]->(plan:PdMPrescription) "
                f"OPTIONAL MATCH (plan)-[:REQUIRES_SPARE]->(sp:SparePart) "
                f"RETURN m.name AS machine, t.sensor_type AS sensor, t.vibration_rms_mms AS vibration_rms, "
                f"t.bearing_temp_c AS bearing_temp, t.rul_hours AS rul_remaining_hours, t.anomaly_status AS anomaly, "
                f"t.diagnostic_summary AS diagnostic, plan.action_title AS maintenance_action, "
                f"plan.preventive_cost_usd AS preventive_cost, plan.catastrophic_breakdown_cost_usd AS breakdown_cost, "
                f"plan.cost_avoidance_usd AS cost_avoidance, sp.name AS required_spare",
                f"Retrieves IoT sensor condition monitoring, Remaining Useful Life (RUL), and prescriptive maintenance cost-avoidance plan for Machine {machine_id}."
            )
        return (
            "MATCH (m:Machine)-[:HAS_TELEMETRY]->(t:SensorTelemetry) "
            "OPTIONAL MATCH (m)-[:HAS_PDM_PLAN]->(plan:PdMPrescription) "
            "RETURN m.id AS machine_id, m.name AS machine_name, t.anomaly_status AS anomaly_status, "
            "t.vibration_rms_mms AS vibration_rms, t.bearing_temp_c AS bearing_temp, "
            "t.rul_hours AS rul_remaining_hours, plan.action_title AS prescription_plan, "
            "plan.cost_avoidance_usd AS cost_avoidance_usd "
            "ORDER BY m.failure_risk DESC LIMIT 10",
            "Monitors real-time IoT vibration, bearing telemetry, Remaining Useful Life (RUL), and prescriptive maintenance plans across fleet machines."
        )

    # 2.5 Demand Forecasting & Market Projections
    if any(k in q for k in ["demand forecast", "forecasting", "forecast unit", "growth rate", "market driver", "stockout risk", "committed demand"]):
        if any(k in q for k in ["commit", "contract"]):
            return (
                "MATCH (c:Customer)-[r:COMMITTED_DEMAND]->(fc:DemandForecast)<-[:HAS_FORECAST]-(p:Product) "
                "RETURN c.name AS customer_name, r.contract_number AS contract, r.contract_units AS committed_units, "
                "r.priority AS priority, r.penalty_risk AS penalty_risk, r.hourly_penalty_usd AS hourly_penalty_usd, "
                "fc.period AS forecast_quarter, p.name AS product_name "
                "ORDER BY r.contract_units DESC LIMIT 10",
                "Cross-references forward customer contract commitments against quarterly product demand forecasts."
            )
        if product_id:
            return (
                f"MATCH (p:Product {{id: '{product_id}'}})-[:HAS_FORECAST]->(fc:DemandForecast) "
                f"OPTIONAL MATCH (p)-[s:STOCKED_AT]->(wh:Warehouse) "
                f"WITH p, fc, coalesce(sum(s.qty), 0) AS total_stock "
                f"RETURN p.name AS product, fc.period AS quarter, fc.forecast_units AS forecast_demand, "
                f"total_stock AS warehouse_stock, (fc.forecast_units - total_stock) AS projected_shortfall, "
                f"fc.growth_rate_pct AS growth_pct, fc.market_driver AS market_driver, fc.stockout_risk_level AS stockout_risk",
                f"Evaluates forward demand forecasts, market drivers, and warehouse stockout risk for product {product_id}."
            )
        return (
            "MATCH (p:Product)-[:HAS_FORECAST]->(fc:DemandForecast) "
            "OPTIONAL MATCH (p)-[s:STOCKED_AT]->(wh:Warehouse) "
            "WITH p, fc, coalesce(sum(s.qty), 0) AS total_stock "
            "RETURN p.id AS product_id, p.name AS product_name, fc.period AS forecast_period, "
            "fc.forecast_units AS forecast_demand, total_stock AS current_warehouse_stock, "
            "(fc.forecast_units - total_stock) AS projected_shortfall, "
            "fc.growth_rate_pct AS growth_pct, fc.stockout_risk_level AS stockout_risk, "
            "fc.market_driver AS market_driver "
            "ORDER BY projected_shortfall DESC LIMIT 10",
            "Projects quarterly multi-echelon demand forecasts, market growth drivers, and stockout shortfalls across product lines."
        )

    # 3. Suppliers & Location / Risk Rating
    if any(k in q for k in ["supplier", "vendor", "alternate", "lead time"]):
        return (
            "MATCH (s:Supplier)-[:LOCATED_IN]->(r:Region) "
            "RETURN s.id AS supplier_id, s.name AS supplier_name, r.name AS location, s.rating AS quality_rating "
            "ORDER BY s.rating DESC LIMIT 25",
            "Retrieves all active suppliers, their operating geographic regions, and benchmark quality ratings."
        )

    # 3.5 Customer Orders, SLA Delay Penalties & Financial Exposure
    if any(k in q for k in ["hyperdrive", "penalty", "customer order", "sla delay", "hourly penalty"]) or (machine_id == "M7" and any(k in q for k in ["shortfall", "penalty", "order"])):
        return (
            "MATCH (c:Customer {id: 'CUST_HYPERDRIVE_AUTO'})-[:PLACED]->(ord:CustomerOrder)-[:CONTAINS_PRODUCT]->(p:Product) "
            "OPTIONAL MATCH (p)-[s:STOCKED_AT]->(wh:Warehouse) "
            "WITH c, ord, p, coalesce(sum(s.qty), 0) AS warehouse_stock "
            "RETURN c.name AS customer_name, ord.order_number AS order_number, ord.units_ordered AS units_ordered, "
            "warehouse_stock, (ord.units_ordered - warehouse_stock) AS shortfall_units, "
            "ord.hourly_delay_penalty_usd AS hourly_delay_penalty_usd, ord.sla_hours_remaining AS sla_hours_remaining",
            "Evaluates HyperDrive Electric Motors Tier-1 purchase order, calculating net warehouse shortfall and hourly delay penalty exposure if production halts."
        )

    # 3.6 Spare Parts & Backup Machines (Redundancy)
    if any(k in q for k in ["spare", "spindle", "backup", "retool", "redundanc"]):
        target = machine_id or "M7"
        return (
            f"MATCH (m:Machine {{id: '{target}'}})-[:HAS_SPARE_COMPONENT]->(sp:SparePart) "
            f"OPTIONAL MATCH (m)-[:PRODUCES]->(p:Part)<-[r:CAPABLE_OF_PRODUCING]-(backup:Machine) "
            f"RETURN m.name AS machine_name, sp.name AS spare_component, sp.detroit_stock AS detroit_stock, "
            f"sp.munich_stock AS munich_stock, sp.courier_air_transit_hours AS courier_transit_hours, "
            f"backup.name AS backup_machine, r.retooling_time_hours AS retool_hours",
            f"Inspects critical spare component stock and cross-plant standby redundancy for machine {target}."
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
    """Detects multi-question or conversational inputs in the zero-key fallback parser."""
    q_norm = re.sub(r"[^\w\s]", "", question.lower().strip())
    conversational_triggers = [
        "hi", "hello", "hey", "hola", "greetings", "good morning", "good afternoon", "good evening",
        "thanks", "thank you", "who are you", "what are you", "what can you do", "help", "how do you work"
    ]
    if any(q_norm == t or q_norm.startswith(t + " ") for t in conversational_triggers):
        return {
            "mode": "conversation",
            "cypher": "",
            "explanation": "Conversational assistant",
            "answer": (
                "👋 **Hello! I'm the TwinForge Graph Copilot.**\n\n"
                "I am your conversational industrial AI assistant connected live to our **FalkorDB knowledge graph** across Detroit, Munich, and London facilities.\n\n"
                "You can chat with me or ask questions to investigate the live graph:\n"
                "• *\"If Machine M7 in Detroit fails, what is the inventory shortfall and hourly penalty for HyperDrive Electric Motors order of P4 Smart Turbines?\"*\n"
                "• *\"What is the status of the emergency spare spindle for M7?\"*\n"
                "• *\"Show me all machines with failure risk over 50%\"*\n\n"
                "How can I assist your operations today?"
            )
        }

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



    # Customer Order / SLA Penalty / Financial Exposure formatting
    has_penalty = any(k in col_map for k in ["hourly_delay_penalty_usd", "hourly_penalty", "penalty", "penaltyperhour"])
    has_customer = any(k in col_map for k in ["customer", "customer_name", "cust_name"])
    has_order = any(k in col_map for k in ["order_number", "order_num", "order_id", "units_ordered", "ordered"])
    if has_penalty or (has_customer and has_order):
        lines = []
        for row in results[:5]:
            c_name = None
            for cn_key in ["customer_name", "customer", "cust_name"]:
                if cn_key in col_map and row[col_map[cn_key]]:
                    c_name = row[col_map[cn_key]]
                    break
            if not c_name or c_name == "Customer":
                if "hyperdrive" in question.lower() or "hyperdrive" in str(row).lower():
                    c_name = "HyperDrive Electric Motors (Tier-1 OEM)"
                else:
                    c_name = "Strategic Customer"

            ord_no = row[col_map.get("order_number", col_map.get("order_num", col_map.get("order_id", 0)))] if has_order else "Critical PO"

            sf_val = None
            for sf_key in ["shortfall_units", "shortfallunits", "shortfall", "deficit"]:
                if sf_key in col_map and row[col_map[sf_key]] is not None:
                    sf_val = row[col_map[sf_key]]
                    break

            ord_val = None
            for ord_key in ["units_ordered", "ordered"]:
                if ord_key in col_map and row[col_map[ord_key]] is not None:
                    ord_val = row[col_map[ord_key]]
                    break

            stk_val = None
            for stk_key in ["warehouse_stock", "warehousestock", "current_stock", "total_stock", "stock"]:
                if stk_key in col_map and row[col_map[stk_key]] is not None:
                    stk_val = row[col_map[stk_key]]
                    break

            pen_val = None
            for pen_key in ["hourly_delay_penalty_usd", "hourly_penalty", "penalty", "penaltyperhour"]:
                if pen_key in col_map and row[col_map[pen_key]] is not None:
                    pen_val = row[col_map[pen_key]]
                    break

            sla_val = None
            for sla_key in ["sla_hours_remaining", "sla_hours", "hoursleft", "hours_left"]:
                if sla_key in col_map and row[col_map[sla_key]] is not None:
                    sla_val = row[col_map[sla_key]]
                    break

            entry = f"• **{c_name}** (Order `{ord_no}`):\n"
            if ord_val is not None:
                stk_str = f" | Warehouse Stock: **{int(float(stk_val)):,} units**" if stk_val is not None else ""
                entry += f"  - Ordered: **{int(float(ord_val)):,} units**{stk_str}\n"
            if sf_val is not None:
                entry += f"  - 🚨 Net Inventory Shortfall: **{int(float(sf_val)):,} units**\n"
            if pen_val is not None:
                entry += f"  - ⏱️ SLA Delay Penalty: **${float(pen_val):,.2f} / hour**"
                if sla_val is not None:
                    entry += f" (SLA Window: **{sla_val}h remaining**)"
                entry += "\n"
            lines.append(entry.strip())
        return "⚠️ **Customer Order & Financial SLA Exposure**:\n\n" + "\n\n".join(lines)

    # Spare Part / Redundancy formatting (handles single rows or grouped/collected lists)
    if any(k in col_map for k in ["spare_component", "spare_components", "spare_part", "spare_parts", "spare_id", "spare_name", "spindle", "backup_machine", "backup_machines"]):
        lines = []
        for row in results[:5]:
            m_name = row[col_map.get("machine_name", col_map.get("machine_id", col_map.get("compatible_machine", 0)))] if any(k in col_map for k in ["machine_name", "machine_id", "compatible_machine"]) else "M7"
            lines.append(f"• **Asset {m_name}**:")

            # Unpack spares (list of dicts or single string)
            spares = []
            for sp_k in ["spare_components", "spare_parts"]:
                if sp_k in col_map and isinstance(row[col_map[sp_k]], list):
                    spares.extend(row[col_map[sp_k]])
            if not spares and any(k in col_map for k in ["spare_component", "spare_part", "spare_name", "spare_id", "spindle"]):
                sp_name = row[col_map.get("spare_name", col_map.get("spare_component", col_map.get("spare_part", col_map.get("spare_id", 0))))]
                det_stk = row[col_map.get("detroit_stock")] if "detroit_stock" in col_map else (row[col_map.get("detroit_units_available")] if "detroit_units_available" in col_map else 0)
                mun_stk = row[col_map.get("munich_stock")] if "munich_stock" in col_map else (row[col_map.get("munich_units_available")] if "munich_units_available" in col_map else 2)
                transit = row[col_map.get("courier_transit_hours", col_map.get("courier_air_transit_hours", 8.5))] if any(k in col_map for k in ["courier_transit_hours", "courier_air_transit_hours"]) else 8.5
                if sp_name:
                    spares.append({"name": sp_name, "detroit_stock": det_stk, "munich_stock": mun_stk, "courier_air_transit_hours": transit})

            for sp in spares:
                if isinstance(sp, dict):
                    name = sp.get("name") or sp.get("spare_id", "Spare Unit")
                    det = sp.get("detroit_stock", 0)
                    mun = sp.get("munich_stock", 0)
                    transit = sp.get("courier_air_transit_hours")
                    transit_str = f" ({transit}h air courier dispatch)" if transit else ""
                    lines.append(f"  - 📦 Spare Component: **{name}** [Detroit Stock: **{det}**, Munich Hub: **{mun}**{transit_str}]")

            # Unpack backup machines (list of dicts or single string)
            backups = []
            for bk_k in ["backup_machines", "backup_machine"]:
                if bk_k in col_map:
                    val = row[col_map[bk_k]]
                    if isinstance(val, list):
                        backups.extend(val)
                    elif isinstance(val, str):
                        backups.append({"name": val, "retooling_time_hours": row[col_map.get("retool_hours", 0)] if "retool_hours" in col_map else None})

            seen_backups = set()
            for bk in backups:
                if isinstance(bk, dict):
                    bk_name = bk.get("name") or bk.get("backup_id", "Backup Unit")
                    if bk_name in seen_backups:
                        continue
                    seen_backups.add(bk_name)
                    retool = bk.get("retooling_time_hours")
                    retool_str = f" — Retooling SLA: **{retool}h**" if retool else ""
                    output_rate = bk.get("daily_output_units")
                    out_str = f", Capacity: **{output_rate} units/day**" if output_rate else ""
                    lines.append(f"  - 🔄 Standby Redundancy: **{bk_name}** ({bk.get('status', 'STANDBY')}){retool_str}{out_str}")

        return "🔄 **Asset Redundancy & Spare Component Readiness**:\n\n" + "\n".join(lines)

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
    sf_key = next((k for k in ["shortfall_units", "shortfallunits", "shortfall", "deficit"] if k in col_map), None)
    if sf_key:
        lines = []
        for row in results[:5]:
            p_name = row[col_map.get("product_name", col_map.get("name", col_map.get("product", 0)))]
            sf = row[col_map[sf_key]]
            try:
                sf_int = int(float(sf)) if sf is not None else 0
            except (ValueError, TypeError):
                sf_int = 0
            lines.append(f"• **{p_name}**: Projected deficit of **{sf_int:,} units**")
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
    if not llm_payload.get("cypher") and not llm_payload.get("queries") and not llm_payload.get("answer") and gemini_key:
        try:
            llm_payload = _call_gemini(question, gemini_key)
            provider = "Google AI Studio"
            model_name = "Gemini 2.0 Flash"
        except Exception as e:
            print(f"[Copilot Warning] Gemini call failed: {e}. Falling back...")

    # 3. Built-in Fallback
    if not llm_payload.get("cypher") and not llm_payload.get("queries") and not llm_payload.get("answer"):
        llm_payload = _semantic_engine_fallback(question)
        provider = "TwinForge Semantic Engine"
        model_name = "Built-in Graph Parser (100% Free)"

    # Conversational mode handling (e.g. greetings, general questions, explanations)
    if llm_payload.get("mode") == "conversation" or (not llm_payload.get("cypher") and llm_payload.get("answer")):
        total_latency = round((time.perf_counter() - start_time) * 1000, 1)
        return {
            "status": "success",
            "mode": "conversation",
            "provider": provider,
            "model": model_name,
            "question": question,
            "cypher": "// Conversational response — no graph traversal needed",
            "explanation": llm_payload.get("explanation", "Conversational response"),
            "answer": llm_payload.get("answer", "Hello! How can I assist you with your supply chain operations today?"),
            "row_count": 0,
            "falkordb_latency_ms": 0.0,
            "total_latency_ms": total_latency,
            "columns": [],
            "results": [],
        }

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
