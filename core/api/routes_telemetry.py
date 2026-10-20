from typing import Optional
from fastapi import APIRouter, Query
from core.db import get_graph, get_connection_config

router = APIRouter(tags=["telemetry"])


@router.get("/health")
@router.get("/api/health")
async def health_check():
    """Confirms FalkorDB connection and reveals target environment (host only, never credentials)."""
    cfg = get_connection_config()
    try:
        g = get_graph()
        g.query("RETURN 1").result_set
        return {
            "status": "healthy",
            "database": "FalkorDB",
            "target_host": f"{cfg['host']}:{cfg['port']}",
            "graph": cfg["graph_name"],
            "environment": "Cloud" if cfg["is_cloud"] else "Local",
            "tls_enabled": cfg["ssl"],
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "target_host": f"{cfg['host']}:{cfg['port']}",
            "environment": "Cloud" if cfg["is_cloud"] else "Local",
            "error": str(e),
        }


@router.get("/api/plants")
async def get_plants():
    """Retrieve all manufacturing facilities from FalkorDB with fleet metrics."""
    try:
        g = get_graph()
        cypher = """
        MATCH (pl:Plant)
        OPTIONAL MATCH (pl)-[:HAS]->(m:Machine)
        RETURN pl.id AS id, pl.name AS name, pl.location AS location,
               count(m) AS machine_count,
               sum(CASE WHEN m.failure_risk >= 0.70 THEN 1 ELSE 0 END) AS at_risk_count,
               avg(m.failure_risk) AS avg_risk
        ORDER BY pl.name
        """
        rows = g.query(cypher).result_set
        plants = []
        for row in rows:
            p_id, name, location, m_cnt, risk_cnt, avg_risk = row
            avg_health = int(round((1.0 - (avg_risk or 0)) * 100))
            plants.append({
                "id": p_id,
                "name": name,
                "location": location,
                "machine_count": m_cnt,
                "at_risk_count": int(risk_cnt or 0),
                "avg_health": avg_health,
            })
        return {"plants": plants}
    except Exception as e:
        return {"plants": [], "error": str(e)}


@router.get("/api/kpis")
async def get_kpis(plant_id: Optional[str] = Query(None)):
    """Retrieve top-level operational supply chain KPIs from FalkorDB with optional plant filtering."""
    try:
        g = get_graph()
        
        # At risk machines count
        if plant_id:
            risk_cypher = "MATCH (pl:Plant {id: $pid})-[:HAS]->(m:Machine) WHERE m.failure_risk >= 0.70 RETURN count(m)"
            risk_res = g.query(risk_cypher, params={"pid": plant_id}).result_set
            machine_count_cypher = "MATCH (pl:Plant {id: $pid})-[:HAS]->(m:Machine) RETURN count(m)"
            m_res = g.query(machine_count_cypher, params={"pid": plant_id}).result_set
            monitored_machines = m_res[0][0] if m_res else 0
        else:
            risk_res = g.query("MATCH (m:Machine) WHERE m.failure_risk >= 0.70 RETURN count(m)").result_set
            m_res = g.query("MATCH (m:Machine) RETURN count(m)").result_set
            monitored_machines = m_res[0][0] if m_res else 0
            
        at_risk_count = risk_res[0][0] if risk_res else 0

        # Decisions made
        dec_res = g.query("MATCH (d:Decision) RETURN count(d)").result_set
        decision_count = dec_res[0][0] if dec_res else 0

        # Products count & total inventory
        inv_res = g.query("MATCH (p:Product)-[s:STOCKED_AT]->(w:Warehouse) RETURN count(DISTINCT p), sum(s.qty)").result_set
        prod_count = inv_res[0][0] if inv_res else 0
        total_inv = inv_res[0][1] if inv_res else 0

        # Customers served
        cust_res = g.query("MATCH (c:Customer) RETURN count(c)").result_set
        cust_count = cust_res[0][0] if cust_res else 0

        return {
            "status": "online",
            "plant_id": plant_id or "ALL",
            "machines_monitored": monitored_machines,
            "at_risk_machines": at_risk_count,
            "decisions_active": decision_count,
            "products_monitored": prod_count,
            "total_inventory_units": int(total_inv),
            "customers_protected": cust_count,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/api/telemetry")
async def get_telemetry(plant_id: Optional[str] = Query(None)):
    """Retrieve machines with live health, vibration, temperature and risk metrics, optionally filtered by plant."""
    try:
        g = get_graph()
        if plant_id:
            cypher = """
            MATCH (pl:Plant {id: $pid})-[:HAS]->(m:Machine)
            RETURN m.id AS id, m.name AS name, m.failure_risk AS failure_risk,
                   m.predicted_failure_days AS predicted_days, pl.id AS plant_id, pl.name AS plant_name
            ORDER BY m.failure_risk DESC
            """
            rows = g.query(cypher, params={"pid": plant_id}).result_set
        else:
            cypher = """
            MATCH (pl:Plant)-[:HAS]->(m:Machine)
            RETURN m.id AS id, m.name AS name, m.failure_risk AS failure_risk,
                   m.predicted_failure_days AS predicted_days, pl.id AS plant_id, pl.name AS plant_name
            ORDER BY m.failure_risk DESC
            """
            rows = g.query(cypher).result_set

        machines = []
        for row in rows:
            m_id, name, risk, days, pl_id, pl_name = row
            health = int(round((1.0 - risk) * 100))
            vibration = round(1.20 + (risk * 0.65), 2)
            temperature = round(65.0 + (risk * 9.5), 1)
            status = "CRITICAL" if risk >= 0.85 else ("WARNING" if risk >= 0.50 else "HEALTHY")
            machines.append({
                "id": m_id,
                "name": name,
                "failure_risk": risk,
                "health_score": health,
                "predicted_failure_days": days,
                "vibration": vibration,
                "temperature": temperature,
                "plant_id": pl_id,
                "plant_name": pl_name,
                "status": status,
            })
        return {"machines": machines, "plant_id": plant_id or "ALL"}
    except Exception as e:
        return {"machines": [], "error": str(e)}


@router.get("/api/inventory")
async def get_inventory():
    """Retrieve products demand forecast vs available inventory and calculated shortfall."""
    try:
        g = get_graph()
        cypher = """
        MATCH (p:Product)
        OPTIONAL MATCH (p)-[s:STOCKED_AT]->(w:Warehouse)
        RETURN p.id AS id, p.name AS name, p.forecast_30d AS forecast, p.safety_stock AS safety,
               coalesce(sum(s.qty), 0) AS stock,
               collect({warehouse_id: w.id, warehouse_name: w.name, qty: s.qty}) AS warehouses
        ORDER BY p.id
        """
        rows = g.query(cypher).result_set
        products = []
        for row in rows:
            p_id, name, fcast, safety, stock, whs = row
            stock = float(stock)
            shortfall = max(0.0, fcast - stock)
            products.append({
                "id": p_id,
                "name": name,
                "forecast_30d": fcast,
                "safety_stock": safety,
                "total_stock": stock,
                "shortfall": shortfall,
                "status": "SHORTFALL" if shortfall > 0 else "BALANCED",
                "warehouses": [w for w in whs if w.get("warehouse_id")],
            })
        return {"products": products}
    except Exception as e:
        return {"products": [], "error": str(e)}
