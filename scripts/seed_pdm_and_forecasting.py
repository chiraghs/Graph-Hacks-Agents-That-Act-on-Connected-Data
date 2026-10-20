"""scripts/seed_pdm_and_forecasting.py - Seeds Predictive Maintenance and Demand Forecasting graph dataset.

Adds:
1. SensorTelemetry nodes linked to Machines via [:HAS_TELEMETRY]
   - Detailed IoT metrics: vibration_rms_mms, bearing_temp_c, acoustic_emission_db,
     operating_hours, rul_hours (Remaining Useful Life), health_index, anomaly_status.
2. PdMPrescription nodes linked via [:HAS_PDM_PLAN] and [:REQUIRES_SPARE]
   - Prescriptive maintenance plans, intervention windows, scheduled downtime,
     preventive vs catastrophic breakdown costs, and cost avoidance calculations.
3. DemandForecast nodes linked to Products via [:HAS_FORECAST]
   - Multi-quarter forecast horizons (Q2/Q3 2026), confidence intervals (lower/upper),
     growth rates, market drivers, and projected stockout risk.
4. Committed customer demand links via [:COMMITTED_DEMAND]
   - Ties strategic customers (including HyperDrive Electric Motors) to forecast nodes.
"""

import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.db import get_graph, get_connection_config

def seed_pdm_and_forecasting():
    print("=" * 70)
    print("Seeding Predictive Maintenance & Demand Forecasting Dataset")
    print("=" * 70)

    g = get_graph()
    cfg = get_connection_config()
    print(f"Target Graph: {cfg['graph_name']} on {cfg['host']}:{cfg['port']}")

    # -------------------------------------------------------------
    # 1. SENSOR TELEMETRY & IOT CONDITION MONITORING
    # -------------------------------------------------------------
    print("1/4. Creating SensorTelemetry IoT nodes & [:HAS_TELEMETRY] relationships...")

    telemetry_data = [
        # M7 (Critical Machine in Detroit - Bearing Spalling)
        {
            "sensor_id": "SENSOR_M7_VIB_SPINDLE",
            "machine_id": "M7",
            "sensor_type": "High-Frequency Triaxial Accelerometer & RTD Temp Probe",
            "vibration_rms_mms": 8.45,
            "vibration_threshold_mms": 4.50,
            "bearing_temp_c": 89.4,
            "normal_temp_c": 65.0,
            "acoustic_emission_db": 94.2,
            "lubricant_particle_ppm": 385,
            "operating_hours": 8420,
            "rul_hours": 48.0,  # 2 days remaining useful life
            "health_index": 0.18,
            "anomaly_status": "CRITICAL_BEARING_DEGRADATION",
            "diagnostic_summary": "FFT spectrum identifies 240Hz cage fault harmonic; micro-spalling on inner ceramic raceway.",
            "last_calibrated": "2026-03-15",
            "recommended_inspection": "Immediate emergency shutdown or load derating"
        },
        # M12 (Harmless Filter Clog in Detroit)
        {
            "sensor_id": "SENSOR_M12_HYDRAULIC_FLOW",
            "machine_id": "M12",
            "sensor_type": "Differential Pressure Transducer & Flow Meter",
            "vibration_rms_mms": 2.05,
            "vibration_threshold_mms": 4.50,
            "bearing_temp_c": 67.2,
            "normal_temp_c": 65.0,
            "acoustic_emission_db": 56.4,
            "lubricant_particle_ppm": 85,
            "operating_hours": 6120,
            "rul_hours": 96.0,  # 4 days
            "health_index": 0.45,
            "anomaly_status": "FILTER_MESH_OCCLUSION",
            "diagnostic_summary": "Differential pressure delta at 3.8 bar exceeds 2.5 bar filter threshold. Hydraulic bypass engaged.",
            "last_calibrated": "2026-02-28",
            "recommended_inspection": "Cartridge flush during scheduled weekend shift"
        },
        # M18 (Standby Redundancy in Detroit - High Health)
        {
            "sensor_id": "SENSOR_M18_STANDBY_MONITOR",
            "machine_id": "M18",
            "sensor_type": "Multi-Parameter Standby Condition Monitor",
            "vibration_rms_mms": 1.12,
            "vibration_threshold_mms": 4.50,
            "bearing_temp_c": 38.5,
            "normal_temp_c": 65.0,
            "acoustic_emission_db": 44.1,
            "lubricant_particle_ppm": 22,
            "operating_hours": 1420,
            "rul_hours": 3600.0,
            "health_index": 0.98,
            "anomaly_status": "OPTIMAL_STANDBY",
            "diagnostic_summary": "Warm idle status verified. Spindle runout within 1.2 microns. Ready for immediate production cutover.",
            "last_calibrated": "2026-04-01",
            "recommended_inspection": "Routine monthly check"
        },
        # M1 (Detroit)
        {
            "sensor_id": "SENSOR_M1_HEALTH",
            "machine_id": "M1",
            "sensor_type": "Triaxial Accelerometer",
            "vibration_rms_mms": 1.35,
            "vibration_threshold_mms": 4.50,
            "bearing_temp_c": 64.1,
            "normal_temp_c": 65.0,
            "acoustic_emission_db": 51.2,
            "lubricant_particle_ppm": 35,
            "operating_hours": 4200,
            "rul_hours": 2400.0,
            "health_index": 0.92,
            "anomaly_status": "NOMINAL",
            "diagnostic_summary": "Baseline telemetry within normal standard deviations.",
            "last_calibrated": "2026-01-10",
            "recommended_inspection": "Quarterly inspection"
        },
        # M13 (Munich CNC)
        {
            "sensor_id": "SENSOR_M13_HEALTH",
            "machine_id": "M13",
            "sensor_type": "Triaxial Accelerometer",
            "vibration_rms_mms": 1.42,
            "vibration_threshold_mms": 4.50,
            "bearing_temp_c": 66.0,
            "normal_temp_c": 65.0,
            "acoustic_emission_db": 53.0,
            "lubricant_particle_ppm": 40,
            "operating_hours": 5100,
            "rul_hours": 2100.0,
            "health_index": 0.89,
            "anomaly_status": "NOMINAL",
            "diagnostic_summary": "Nominal operational telemetry.",
            "last_calibrated": "2026-02-15",
            "recommended_inspection": "Quarterly inspection"
        }
    ]

    g.query("""
    UNWIND $batch AS t
    MERGE (tel:SensorTelemetry {id: t.sensor_id})
    SET 
        tel.sensor_type = t.sensor_type,
        tel.vibration_rms_mms = t.vibration_rms_mms,
        tel.vibration_threshold_mms = t.vibration_threshold_mms,
        tel.bearing_temp_c = t.bearing_temp_c,
        tel.normal_temp_c = t.normal_temp_c,
        tel.acoustic_emission_db = t.acoustic_emission_db,
        tel.lubricant_particle_ppm = t.lubricant_particle_ppm,
        tel.operating_hours = t.operating_hours,
        tel.rul_hours = t.rul_hours,
        tel.health_index = t.health_index,
        tel.anomaly_status = t.anomaly_status,
        tel.diagnostic_summary = t.diagnostic_summary,
        tel.last_calibrated = t.last_calibrated,
        tel.recommended_inspection = t.recommended_inspection
    WITH tel, t
    MATCH (m:Machine {id: t.machine_id})
    MERGE (m)-[:HAS_TELEMETRY]->(tel)
    """, params={"batch": telemetry_data})

    # -------------------------------------------------------------
    # 2. PREDICTIVE MAINTENANCE PRESCRIPTIONS (PdMPrescription)
    # -------------------------------------------------------------
    print("2/4. Creating PdMPrescription nodes, [:HAS_PDM_PLAN] & [:REQUIRES_SPARE]...")

    pdm_plans = [
        {
            "plan_id": "PDM_PLAN_M7_OVERHAUL",
            "machine_id": "M7",
            "spare_id": "SPARE_SPINDLE_KUKA_M7",
            "action_title": "Prescriptive Spindle Overhaul & Ceramic Bearing Replacement",
            "intervention_window_hours": 48.0,
            "scheduled_downtime_hours": 4.0,
            "preventive_cost_usd": 4800.0,
            "catastrophic_breakdown_cost_usd": 145000.0,
            "cost_avoidance_usd": 140200.0,
            "urgency": "CRITICAL_URGENT",
            "technician_cert_required": "Level 3 Mechatronics Specialist",
            "retooling_reroute_target": "M18",
            "steps": [
                "1. Derate M7 feed rate to 40% immediately to prevent catastrophic tool wreck.",
                "2. Dispatch Munich spare spindle via DHL Express Air (8.5h transit).",
                "3. Reroute P4 rotor machining to standby CNC M18 (3.5h retool).",
                "4. Perform scheduled 4-hour hot-swap replacement when spare arrives."
            ]
        },
        {
            "plan_id": "PDM_PLAN_M12_FLUSH",
            "machine_id": "M12",
            "spare_id": "",
            "action_title": "Hydraulic Filter Flush & Fluid Cleanse",
            "intervention_window_hours": 96.0,
            "scheduled_downtime_hours": 1.5,
            "preventive_cost_usd": 650.0,
            "catastrophic_breakdown_cost_usd": 28000.0,
            "cost_avoidance_usd": 27350.0,
            "urgency": "MODERATE_SCHEDULED",
            "technician_cert_required": "Level 1 Maintenance Tech",
            "retooling_reroute_target": "None (Buffer stock sufficient)",
            "steps": [
                "1. Isolate secondary hydraulic loop during 30-minute shift handover.",
                "2. Swap inline filter cartridge with on-hand warehouse inventory.",
                "3. Flush hydraulic return reservoir and reset pressure sensor."
            ]
        }
    ]

    for plan in pdm_plans:
        g.query("""
        MERGE (pdm:PdMPrescription {id: $plan_id})
        SET 
            pdm.action_title = $action_title,
            pdm.intervention_window_hours = $intervention_window_hours,
            pdm.scheduled_downtime_hours = $scheduled_downtime_hours,
            pdm.preventive_cost_usd = $preventive_cost_usd,
            pdm.catastrophic_breakdown_cost_usd = $catastrophic_breakdown_cost_usd,
            pdm.cost_avoidance_usd = $cost_avoidance_usd,
            pdm.urgency = $urgency,
            pdm.technician_cert_required = $technician_cert_required,
            pdm.retooling_reroute_target = $retooling_reroute_target
        WITH pdm
        MATCH (m:Machine {id: $machine_id})
        MERGE (m)-[:HAS_PDM_PLAN]->(pdm)
        """, params={
            "plan_id": plan["plan_id"],
            "machine_id": plan["machine_id"],
            "action_title": plan["action_title"],
            "intervention_window_hours": plan["intervention_window_hours"],
            "scheduled_downtime_hours": plan["scheduled_downtime_hours"],
            "preventive_cost_usd": plan["preventive_cost_usd"],
            "catastrophic_breakdown_cost_usd": plan["catastrophic_breakdown_cost_usd"],
            "cost_avoidance_usd": plan["cost_avoidance_usd"],
            "urgency": plan["urgency"],
            "technician_cert_required": plan["technician_cert_required"],
            "retooling_reroute_target": plan["retooling_reroute_target"],
        })

        if plan["spare_id"]:
            g.query("""
            MATCH (pdm:PdMPrescription {id: $plan_id})
            MATCH (sp:SparePart {id: $spare_id})
            MERGE (pdm)-[:REQUIRES_SPARE]->(sp)
            """, params={"plan_id": plan["plan_id"], "spare_id": plan["spare_id"]})

    # -------------------------------------------------------------
    # 3. DEMAND FORECASTING (DemandForecast)
    # -------------------------------------------------------------
    print("3/4. Creating DemandForecast nodes & [:HAS_FORECAST]...")

    forecast_data = [
        # P4 Smart Turbine Module - High surge
        {
            "id": "FC_P4_2026Q2",
            "product_id": "P4",
            "period": "2026-Q2 (May - Jul 2026)",
            "forecast_units": 1450,
            "confidence_score": 0.94,
            "ci_lower": 1320,
            "ci_upper": 1580,
            "growth_rate_pct": 28.5,
            "market_driver": "North American EV Powertrain Mandate & OEM Fleet Expansion",
            "stockout_risk_level": "CRITICAL",
            "projected_inventory_shortfall": 1050,  # 1450 - 400 warehouse stock
            "days_of_supply_remaining": 11,
            "recommended_production_ramp": "Ramp Detroit Line + Leipzig Redundancy +40%"
        },
        {
            "id": "FC_P4_2026Q3",
            "product_id": "P4",
            "period": "2026-Q3 (Aug - Oct 2026)",
            "forecast_units": 1780,
            "confidence_score": 0.89,
            "ci_lower": 1600,
            "ci_upper": 1950,
            "growth_rate_pct": 22.8,
            "market_driver": "Automotive Tier-1 Peak Pre-Winter Assembly Ramp",
            "stockout_risk_level": "HIGH",
            "projected_inventory_shortfall": 1380,
            "days_of_supply_remaining": 8,
            "recommended_production_ramp": "Add second shift at Silicon Hill Austin"
        },
        # P12 Digital Flow Controller - Stable demand
        {
            "id": "FC_P12_2026Q2",
            "product_id": "P12",
            "period": "2026-Q2 (May - Jul 2026)",
            "forecast_units": 620,
            "confidence_score": 0.92,
            "ci_lower": 570,
            "ci_upper": 680,
            "growth_rate_pct": 4.8,
            "market_driver": "European Factory Retrofits and Replacement Cycles",
            "stockout_risk_level": "LOW",
            "projected_inventory_shortfall": 0,
            "days_of_supply_remaining": 115,  # 2400 units in stock
            "recommended_production_ramp": "Maintain standard batch cadence"
        },
        # P1 Industrial Core System
        {
            "id": "FC_P1_2026Q2",
            "product_id": "P1",
            "period": "2026-Q2 (May - Jul 2026)",
            "forecast_units": 820,
            "confidence_score": 0.88,
            "ci_lower": 740,
            "ci_upper": 900,
            "growth_rate_pct": 12.0,
            "market_driver": "Aerospace Core Structural Upgrades",
            "stockout_risk_level": "MODERATE",
            "projected_inventory_shortfall": 310,
            "days_of_supply_remaining": 22,
            "recommended_production_ramp": "Procure additional alloy stock"
        }
    ]

    g.query("""
    UNWIND $batch AS f
    MERGE (fc:DemandForecast {id: f.id})
    SET 
        fc.period = f.period,
        fc.forecast_units = f.forecast_units,
        fc.confidence_score = f.confidence_score,
        fc.ci_lower = f.ci_lower,
        fc.ci_upper = f.ci_upper,
        fc.growth_rate_pct = f.growth_rate_pct,
        fc.market_driver = f.market_driver,
        fc.stockout_risk_level = f.stockout_risk_level,
        fc.projected_inventory_shortfall = f.projected_inventory_shortfall,
        fc.days_of_supply_remaining = f.days_of_supply_remaining,
        fc.recommended_production_ramp = f.recommended_production_ramp
    WITH fc, f
    MATCH (p:Product {id: f.product_id})
    MERGE (p)-[:HAS_FORECAST]->(fc)
    """, params={"batch": forecast_data})

    # -------------------------------------------------------------
    # 4. COMMITTED DEMAND CONTRACTS (Customer -> DemandForecast)
    # -------------------------------------------------------------
    print("4/4. Linking Strategic Customers to Forecasts via [:COMMITTED_DEMAND]...")

    commitments = [
        # HyperDrive Electric Motors (550 contracted units for Q2)
        {
            "customer_id": "CUST_HYPERDRIVE_AUTO",
            "forecast_id": "FC_P4_2026Q2",
            "contract_units": 550,
            "contract_number": "CONTRACT-HYPERDRIVE-Q2-2026",
            "priority": "Tier-1 Mission Critical",
            "penalty_risk": True,
            "hourly_penalty_usd": 25000.0,
            "delivery_window": "2026-05-15 to 2026-06-30"
        },
        # Client Corp 01 (Strategic OEM - 350 contracted units)
        {
            "customer_id": "CUST_001",
            "forecast_id": "FC_P4_2026Q2",
            "contract_units": 350,
            "contract_number": "CONTRACT-APEX-CUST01-2026",
            "priority": "Strategic Partner",
            "penalty_risk": False,
            "hourly_penalty_usd": 0.0,
            "delivery_window": "2026-06-01 to 2026-07-15"
        },
        # Client Corp 02 (Strategic OEM - 250 contracted units)
        {
            "customer_id": "CUST_002",
            "forecast_id": "FC_P4_2026Q2",
            "contract_units": 250,
            "contract_number": "CONTRACT-APEX-CUST02-2026",
            "priority": "Enterprise",
            "penalty_risk": False,
            "hourly_penalty_usd": 0.0,
            "delivery_window": "2026-06-15 to 2026-07-30"
        }
    ]

    g.query("""
    UNWIND $batch AS c
    MATCH (cust:Customer {id: c.customer_id})
    MATCH (fc:DemandForecast {id: c.forecast_id})
    MERGE (cust)-[r:COMMITTED_DEMAND]->(fc)
    SET 
        r.contract_units = c.contract_units,
        r.contract_number = c.contract_number,
        r.priority = c.priority,
        r.penalty_risk = c.penalty_risk,
        r.hourly_penalty_usd = c.hourly_penalty_usd,
        r.delivery_window = c.delivery_window
    """, params={"batch": commitments})

    # Verification counts
    print("-" * 70)
    print("Verification of Added Predictive Maintenance & Forecasting Nodes:")
    for lbl in ["SensorTelemetry", "PdMPrescription", "DemandForecast"]:
        res = g.query(f"MATCH (n:{lbl}) RETURN count(n)").result_set
        print(f"  Nodes (:{lbl:18s}): {res[0][0]}")

    for rel in ["HAS_TELEMETRY", "HAS_PDM_PLAN", "REQUIRES_SPARE", "HAS_FORECAST", "COMMITTED_DEMAND"]:
        res = g.query(f"MATCH ()-[r:{rel}]->() RETURN count(r)").result_set
        print(f"  Rels  [:{rel:18s}]: {res[0][0]}")
    print("=" * 70)


if __name__ == "__main__":
    seed_pdm_and_forecasting()
