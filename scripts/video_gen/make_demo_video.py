#!/usr/bin/env python3
"""scripts/video_gen/make_demo_video.py
Generates a broadcast-quality 1080p MP4 demonstration video for TwinForge & FalkorDB.
Renders high-resolution HTML5 slides via Playwright, generates voiceover with macOS TTS,
and compiles the final MP4 using ffmpeg.
"""

import os
import subprocess
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORK_DIR = os.path.join(BASE_DIR, "scripts", "video_gen", "temp")
OUTPUT_VIDEO = os.path.join(BASE_DIR, "static", "twinforge_demo.mp4")

os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)

# 7 Storyboard Scenes with Visual Slides and Narration Scripts
SCENES = [
    {
        "id": "scene_1_intro",
        "title": "TwinForge: Autonomous Industrial Digital Twin",
        "subtitle": "Powered by FalkorDB Graph Engine • 3,705 Nodes • 5,998 Relationships",
        "narration": "Welcome to TwinForge, an autonomous industrial digital twin and multi-agent supply chain platform powered by FalkorDB. Connected graph data bridges shopfloor telemetry, global logistics, and real-time operational decisions.",
        "html": """
        <div class="card intro-card">
            <div class="badge-row">
                <span class="badge cyan">FalkorDB Property Graph</span>
                <span class="badge green">Multi-Agent System</span>
                <span class="badge blue">Live Digital Twin</span>
            </div>
            <h1 class="main-title">TWIN<span class="highlight">FORGE</span></h1>
            <p class="tagline">Graph-Native Industrial Intelligence & Autonomous Operations</p>
            <div class="grid-stats">
                <div class="stat-box">
                    <div class="stat-num">3,705</div>
                    <div class="stat-label">Graph Nodes</div>
                </div>
                <div class="stat-box">
                    <div class="stat-num">5,998</div>
                    <div class="stat-label">Multi-Hop Edges</div>
                </div>
                <div class="stat-box">
                    <div class="stat-num">2</div>
                    <div class="stat-label">Smart Facilities</div>
                </div>
                <div class="stat-box">
                    <div class="stat-num">&lt; 40ms</div>
                    <div class="stat-label">Query Latency</div>
                </div>
            </div>
            <div class="facility-preview">
                <div class="fac-chip">🏭 Apex Advanced Assembly (Detroit, USA)</div>
                <div class="fac-chip">⚡ Thames Nanotech Foundry (London, UK)</div>
                <div class="fac-chip">🔄 Bavaria Mechatronics Hub (Munich, Germany)</div>
            </div>
        </div>
        """
    },
    {
        "id": "scene_2_telemetry",
        "title": "Critical Telemetry Anomaly Detected",
        "subtitle": "Apex Detroit Facility • CNC-Unit-M7 • Severe Vibration Alarm",
        "narration": "At the Apex Detroit facility, predictive telemetry flags an urgent alarm on CNC-Unit-M7. Thermal excursions and bearing harmonic resonance spike failure risk to 94%, with predicted breakdown in just 5 days.",
        "html": """
        <div class="card">
            <div class="badge-row">
                <span class="badge red">CRITICAL ALERT</span>
                <span class="badge dark">Apex Detroit • Bay 3</span>
            </div>
            <h2 class="section-title">Physical Shopfloor Asset: CNC-Unit-M7</h2>
            <div class="grid-2col">
                <div class="asset-card alert-glow">
                    <div class="asset-header">
                        <span class="asset-id">M7</span>
                        <span class="asset-type">5-Axis Precision CNC Machining Center</span>
                    </div>
                    <div class="telemetry-gauges">
                        <div class="gauge-item">
                            <span class="gauge-label">Failure Probability</span>
                            <span class="gauge-val red-text">94.0%</span>
                            <div class="bar-bg"><div class="bar-fill red-fill" style="width: 94%;"></div></div>
                        </div>
                        <div class="gauge-item">
                            <span class="gauge-label">Predicted Failure Horizon</span>
                            <span class="gauge-val yellow-text">5 Days Remaining</span>
                            <div class="bar-bg"><div class="bar-fill yellow-fill" style="width: 20%;"></div></div>
                        </div>
                        <div class="gauge-item">
                            <span class="gauge-label">Vibration Harmonic Velocity</span>
                            <span class="gauge-val red-text">8.4 mm/s RMS (Norm: &lt; 1.8)</span>
                        </div>
                    </div>
                </div>
                <div class="diagnostic-box">
                    <div class="box-title">Recent FalkorDB Maintenance Logs</div>
                    <ul class="diag-list">
                        <li>⚠️ <b>Thermal Gradient Excursion</b>: 170 min downtime (glycol chiller purge)</li>
                        <li>⚠️ <b>Piezo Sensor Drift</b>: Sub-micron zero-point recalibration</li>
                        <li>⚠️ <b>Vibration Resonance</b>: Multi-axis damping bearings approaching end-of-life</li>
                    </ul>
                    <div class="graph-tag">Connected in FalkorDB: (:Machine {id: 'M7'})-[:HAS_MAINTENANCE_EVENT]-&gt;(:MaintenanceLog)</div>
                </div>
            </div>
        </div>
        """
    },
    {
        "id": "scene_3_traversal",
        "title": "FalkorDB Multi-Hop Blast Radius Traversal",
        "subtitle": "Discovering Downstream Dependencies across Parts, Products, and Warehouses",
        "narration": "FalkorDB traverses 5 hops across the knowledge graph in 35 milliseconds. Machine M7 produces the rotor, stator, and drive shaft for Product P4. Warehouse inventory checks reveal only 400 total units in stock.",
        "html": """
        <div class="card">
            <div class="badge-row">
                <span class="badge cyan">Graph Traversal</span>
                <span class="badge blue">5-Hop Multi-Hop Search</span>
            </div>
            <h2 class="section-title">Downstream Impact Path</h2>
            <div class="traversal-chain">
                <div class="chain-node red-node">
                    <div class="node-type">Machine</div>
                    <div class="node-name">CNC-Unit-M7</div>
                    <div class="node-meta">Risk: 94%</div>
                </div>
                <div class="chain-arrow">PRODUCES ➔</div>
                <div class="chain-node">
                    <div class="node-type">Parts (3)</div>
                    <div class="node-name">Rotor, Shaft, Stator</div>
                    <div class="node-meta">PART_M7_*</div>
                </div>
                <div class="chain-arrow">USED_IN ➔</div>
                <div class="chain-node purple-node">
                    <div class="node-type">Product</div>
                    <div class="node-name">P4 Smart Turbine</div>
                    <div class="node-meta">SKU: P4</div>
                </div>
                <div class="chain-arrow">STOCKED_AT ➔</div>
                <div class="chain-node green-node">
                    <div class="node-type">Warehouses (2)</div>
                    <div class="node-name">Midwest (250) + East (150)</div>
                    <div class="node-meta">Stock: 400 Units</div>
                </div>
            </div>
            <div class="cypher-box">
                <div class="cypher-header">FalkorDB Cypher Traversal:</div>
                <code>MATCH (m:Machine {id: 'M7'})-[:PRODUCES]-&gt;(p:Part)-[:USED_IN]-&gt;(prod:Product {id: 'P4'})<br/>
OPTIONAL MATCH (prod)-[s:STOCKED_AT]-&gt;(w:Warehouse)<br/>
RETURN prod.name, sum(s.qty) AS total_stock // Latency: 35.6ms</code>
            </div>
        </div>
        """
    },
    {
        "id": "scene_4_customer_sla",
        "title": "Customer Order & Financial SLA Exposure",
        "subtitle": "HyperDrive Electric Motors PO-HYPERDRIVE-2026-P4 • $25,000 / Hour Delay Penalty",
        "narration": "Tier-1 customer HyperDrive Electric Motors has a critical purchase order for 550 units of P4 turbines. With only 400 units in warehouse stock, there is an immediate 150-unit deficit, triggering a 25,000 dollar per hour delay penalty clause.",
        "html": """
        <div class="card">
            <div class="badge-row">
                <span class="badge red">SLA Breach Warning</span>
                <span class="badge yellow">Financial Exposure</span>
            </div>
            <h2 class="section-title">Critical Customer Order Breakdown</h2>
            <div class="grid-2col">
                <div class="order-card">
                    <div class="order-client">HyperDrive Electric Motors (Tier-1 OEM)</div>
                    <div class="order-no">PO-HYPERDRIVE-2026-P4 (ORD_APEX_CRITICAL_01)</div>
                    <div class="order-row"><span>Contract Value:</span> <b>$1,650,000 USD</b></div>
                    <div class="order-row"><span>Order Quantity:</span> <b>550 Units</b></div>
                    <div class="order-row"><span>Warehouse Stock:</span> <b>400 Units (WH_MIDWEST + WH_EAST)</b></div>
                    <div class="deficit-callout">
                        <span class="def-num">150 Units</span>
                        <span class="def-text">NET INVENTORY SHORTFALL</span>
                    </div>
                </div>
                <div class="penalty-card">
                    <div class="penalty-title">SLA Penalty Clause</div>
                    <div class="penalty-rate">$25,000 <span class="rate-sub">/ hour</span></div>
                    <div class="sla-clock">⏱️ SLA Window Remaining: <b>72 Hours</b></div>
                    <p class="penalty-desc">Halting M7 production without remediation causes an immediate buffer stockout, triggering contractual breach and severe OEM assembly shutdown fines.</p>
                </div>
            </div>
        </div>
        """
    },
    {
        "id": "scene_5_copilot",
        "title": "TwinForge Conversational Graph Copilot",
        "subtitle": "Natural Language to Cypher • Dynamic Conversational & Graph Execution Modes",
        "narration": "Operators converse naturally with the TwinForge Graph Copilot. It knows when to engage conversationally and when to translate complex questions into optimized Cypher queries, returning grounded executive answers in milliseconds.",
        "html": """
        <div class="card">
            <div class="badge-row">
                <span class="badge cyan">TwinForge Graph Copilot</span>
                <span class="badge green">Meta Llama 3.3 70B + FalkorDB</span>
            </div>
            <h2 class="section-title">Human-AI Interactive Investigation</h2>
            <div class="chat-container">
                <div class="chat-msg user-msg">
                    <div class="sender">Plant Operations VP:</div>
                    <div class="msg-bubble">"If Machine M7 in Detroit fails, what is the inventory shortfall and hourly penalty for HyperDrive Electric Motors order of P4 Smart Turbines?"</div>
                </div>
                <div class="chat-msg ai-msg">
                    <div class="sender">🤖 TwinForge Graph Copilot (Executed on FalkorDB in 35ms):</div>
                    <div class="msg-bubble">
                        <div class="res-badge">⚠️ Customer Order & Financial SLA Exposure:</div>
                        <ul class="chat-bullets">
                            <li><b>HyperDrive Electric Motors (Tier-1 OEM)</b> (Order <code>PO-HYPERDRIVE-2026-P4</code>):</li>
                            <li>Ordered: <b>550 units</b> | Warehouse Stock: <b>400 units</b></li>
                            <li>🚨 Net Inventory Shortfall: <b>150 units</b></li>
                            <li>⏱️ SLA Delay Penalty: <b>$25,000.00 / hour</b> (SLA Window: <b>72h remaining</b>)</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        """
    },
    {
        "id": "scene_6_mitigation",
        "title": "Autonomous Mitigation & Asset Redundancy",
        "subtitle": "Cross-Plant Standby Machine M18 • Munich Hub Air Dispatch Spindle",
        "narration": "FalkorDB reveals the dual mitigation plan: standby machine M18 can retool in 3.5 hours to produce replacement parts at 80 units per day, while an emergency direct-drive spindle unit is dispatched from Munich via chartered air courier.",
        "html": """
        <div class="card">
            <div class="badge-row">
                <span class="badge green">AUTONOMOUS CONTINGENCY</span>
                <span class="badge blue">Dual Recovery Plan</span>
            </div>
            <h2 class="section-title">FalkorDB Discovered Solutions</h2>
            <div class="grid-2col">
                <div class="solution-card">
                    <div class="sol-badge">SOLUTION 1: Cross-Plant Redundancy</div>
                    <div class="sol-title">CNC-Unit-M18 (Standby Asset)</div>
                    <div class="sol-detail">Connected via <code>[:CAPABLE_OF_PRODUCING]</code> for M7 parts</div>
                    <ul class="sol-stats">
                        <li>🔄 Retooling Setup SLA: <b>3.5 Hours</b></li>
                        <li>⚡ Daily Production Output: <b>80 Units / Day</b></li>
                        <li>✅ Shortfall Recovery: Clears 150-unit deficit in &lt; 48h</li>
                    </ul>
                </div>
                <div class="solution-card">
                    <div class="sol-badge">SOLUTION 2: Emergency Component Dispatch</div>
                    <div class="sol-title">KUKA 24,000 RPM Spindle Unit</div>
                    <div class="sol-detail">Connected via <code>[:HAS_SPARE_COMPONENT]</code></div>
                    <ul class="sol-stats">
                        <li>📍 Location: <b>Munich Central Hub (2 units in stock)</b></li>
                        <li>✈️ Chartered Air Transit: <b>8.5 Hours</b> direct to Detroit</li>
                        <li>💰 Replacement Cost: <b>$48,500 USD</b> (Eliminates $25k/hr penalty)</li>
                    </ul>
                </div>
            </div>
        </div>
        """
    },
    {
        "id": "scene_7_summary",
        "title": "Autonomous Decision Logged in FalkorDB",
        "subtitle": "Turning Supply Chain Risk into Operational Resilience",
        "narration": "The multi-agent system approves the contingency plan and logs an immutable decision node into FalkorDB. Connected graph data turns potential supply chain catastrophe into autonomous operational resilience. Experience the future of industrial intelligence with TwinForge.",
        "html": """
        <div class="card summary-card">
            <div class="badge-row">
                <span class="badge green">MISSION ACCOMPLISHED</span>
                <span class="badge cyan">Immutable Audit Trail</span>
            </div>
            <h1 class="summary-title">Autonomous Resilience Verified</h1>
            <div class="decision-receipt">
                <div class="receipt-header">FalkorDB Decision Node Persisted: <code>DEC_APEX_RETOOL_M18</code></div>
                <div class="receipt-body">
                    <div>• <b>Action</b>: Automated Retooling Order issued to CNC-Unit-M18 (Apex Detroit)</div>
                    <div>• <b>Logistics</b>: Air Courier Dispatch triggered for SPARE_SPINDLE_KUKA_M7 (Munich Hub)</div>
                    <div>• <b>Financial Outcome</b>: 100% SLA penalty mitigated ($1.8M potential loss averted)</div>
                    <div>• <b>Customer SLA</b>: HyperDrive PO-HYPERDRIVE-2026-P4 delivery guaranteed within 72h</div>
                </div>
            </div>
            <div class="tech-stack-row">
                <span>FalkorDB Graph Engine</span> • 
                <span>Meta Llama 3.3 70B</span> • 
                <span>FastAPI Microservices</span> • 
                <span>Autonomous Multi-Agent Architecture</span>
            </div>
        </div>
        """
    }
]

CSS_STYLES = """
* { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
body { width: 1920px; height: 1080px; background: #0B0F19; color: #F3F4F6; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; padding: 60px 80px; position: relative; }

/* Background Tech Grid */
body::before {
    content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background-image: linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px);
    background-size: 60px 60px; z-index: 0; pointer-events: none;
}

.header-bar { display: flex; justify-content: space-between; align-items: center; z-index: 10; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 24px; }
.logo-title { font-size: 28px; font-weight: 800; letter-spacing: 2px; color: #FFF; display: flex; align-items: center; gap: 12px; }
.logo-pill { background: #00F0FF; color: #000; font-size: 14px; font-weight: 800; padding: 4px 10px; border-radius: 6px; }
.header-meta { font-size: 18px; color: #9CA3AF; }

.content-container { flex: 1; display: flex; flex-direction: column; justify-content: center; z-index: 10; padding: 30px 0; }
.card { background: rgba(17, 24, 39, 0.85); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 20px; padding: 40px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); backdrop-filter: blur(16px); }

.badge-row { display: flex; gap: 12px; margin-bottom: 18px; }
.badge { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; padding: 6px 14px; border-radius: 6px; }
.badge.cyan { background: rgba(0, 240, 255, 0.15); color: #00F0FF; border: 1px solid rgba(0, 240, 255, 0.4); }
.badge.green { background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.4); }
.badge.red { background: rgba(239, 68, 68, 0.2); color: #EF4444; border: 1px solid rgba(239, 68, 68, 0.5); }
.badge.yellow { background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.4); }
.badge.blue { background: rgba(59, 130, 246, 0.15); color: #3B82F6; border: 1px solid rgba(59, 130, 246, 0.4); }
.badge.dark { background: rgba(255, 255, 255, 0.1); color: #D1D5DB; }

.main-title { font-size: 76px; font-weight: 900; letter-spacing: 4px; color: #FFF; margin-bottom: 10px; }
.highlight { color: #00F0FF; }
.tagline { font-size: 26px; color: #9CA3AF; margin-bottom: 40px; }
.section-title { font-size: 38px; font-weight: 800; color: #FFF; margin-bottom: 24px; }

.grid-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; margin-bottom: 30px; }
.stat-box { background: rgba(31, 41, 55, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); padding: 24px; border-radius: 14px; text-align: center; }
.stat-num { font-size: 48px; font-weight: 800; color: #00F0FF; }
.stat-label { font-size: 16px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 1px; margin-top: 6px; }

.facility-preview { display: flex; gap: 16px; }
.fac-chip { background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.1); padding: 12px 20px; border-radius: 10px; font-size: 16px; color: #D1D5DB; }

.grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
.asset-card { background: rgba(31, 41, 55, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 28px; }
.alert-glow { border-color: rgba(239, 68, 68, 0.6); box-shadow: 0 0 30px rgba(239, 68, 68, 0.15); }
.asset-id { font-size: 32px; font-weight: 900; color: #EF4444; margin-right: 14px; }
.asset-type { font-size: 18px; color: #9CA3AF; }
.telemetry-gauges { margin-top: 24px; display: flex; flex-direction: column; gap: 18px; }
.gauge-item { display: flex; flex-direction: column; gap: 6px; }
.gauge-label { font-size: 15px; color: #9CA3AF; }
.gauge-val { font-size: 24px; font-weight: 800; }
.red-text { color: #EF4444; }
.yellow-text { color: #F59E0B; }
.bar-bg { width: 100%; height: 8px; background: rgba(255, 255, 255, 0.1); border-radius: 4px; overflow: hidden; margin-top: 4px; }
.bar-fill { height: 100%; }
.red-fill { background: #EF4444; }
.yellow-fill { background: #F59E0B; }

.diagnostic-box { background: rgba(31, 41, 55, 0.5); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 28px; display: flex; flex-direction: column; justify-content: space-between; }
.box-title { font-size: 20px; font-weight: 700; color: #FFF; margin-bottom: 16px; }
.diag-list { list-style: none; display: flex; flex-direction: column; gap: 14px; font-size: 17px; color: #D1D5DB; }
.graph-tag { font-family: monospace; font-size: 14px; color: #00F0FF; background: rgba(0, 240, 255, 0.08); padding: 12px; border-radius: 8px; border: 1px solid rgba(0, 240, 255, 0.2); }

.traversal-chain { display: flex; align-items: center; justify-content: space-between; margin: 30px 0; }
.chain-node { background: rgba(31, 41, 55, 0.9); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 14px; padding: 20px 24px; min-width: 200px; text-align: center; }
.chain-node.red-node { border-color: #EF4444; box-shadow: 0 0 20px rgba(239, 68, 68, 0.2); }
.chain-node.purple-node { border-color: #A855F7; box-shadow: 0 0 20px rgba(168, 85, 247, 0.2); }
.chain-node.green-node { border-color: #10B981; box-shadow: 0 0 20px rgba(16, 185, 129, 0.2); }
.node-type { font-size: 12px; text-transform: uppercase; color: #9CA3AF; letter-spacing: 1px; }
.node-name { font-size: 19px; font-weight: 800; color: #FFF; margin: 6px 0; }
.node-meta { font-size: 14px; color: #00F0FF; }
.chain-arrow { font-size: 14px; font-weight: 800; color: #9CA3AF; letter-spacing: 1px; }
.cypher-box { background: #000; border: 1px solid rgba(0, 240, 255, 0.3); border-radius: 12px; padding: 20px; font-family: "SF Mono", Monaco, Menlo, monospace; font-size: 17px; color: #A7F3D0; line-height: 1.6; }
.cypher-header { color: #00F0FF; font-weight: 700; margin-bottom: 6px; }

.order-card { background: rgba(31, 41, 55, 0.8); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 30px; }
.order-client { font-size: 24px; font-weight: 800; color: #00F0FF; }
.order-no { font-size: 16px; color: #9CA3AF; margin-bottom: 20px; font-family: monospace; }
.order-row { display: flex; justify-content: space-between; font-size: 18px; margin-bottom: 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 8px; }
.deficit-callout { background: rgba(239, 68, 68, 0.15); border: 2px solid #EF4444; border-radius: 12px; padding: 18px; text-align: center; margin-top: 20px; }
.def-num { font-size: 40px; font-weight: 900; color: #EF4444; display: block; }
.def-text { font-size: 14px; letter-spacing: 1.5px; font-weight: 700; color: #FCA5A5; }

.penalty-card { background: rgba(31, 41, 55, 0.8); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 16px; padding: 30px; display: flex; flex-direction: column; justify-content: center; }
.penalty-title { font-size: 20px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 1px; }
.penalty-rate { font-size: 64px; font-weight: 900; color: #F59E0B; margin: 10px 0; }
.rate-sub { font-size: 24px; font-weight: 600; color: #9CA3AF; }
.sla-clock { font-size: 22px; color: #FFF; background: rgba(255, 255, 255, 0.08); padding: 12px 18px; border-radius: 10px; margin-bottom: 20px; width: fit-content; }
.penalty-desc { font-size: 17px; color: #D1D5DB; line-height: 1.6; }

.chat-container { display: flex; flex-direction: column; gap: 20px; }
.chat-msg { display: flex; flex-direction: column; gap: 6px; }
.user-msg { align-self: flex-start; max-width: 80%; }
.ai-msg { align-self: flex-start; max-width: 90%; }
.sender { font-size: 15px; font-weight: 700; color: #9CA3AF; }
.user-msg .msg-bubble { background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.5); padding: 18px 24px; border-radius: 14px; font-size: 20px; color: #FFF; font-weight: 500; }
.ai-msg .msg-bubble { background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); padding: 22px 28px; border-radius: 14px; font-size: 18px; color: #FFF; line-height: 1.6; }
.res-badge { color: #F59E0B; font-weight: 800; font-size: 19px; margin-bottom: 10px; }
.chat-bullets { list-style: none; display: flex; flex-direction: column; gap: 8px; margin-top: 10px; font-size: 18px; }

.solution-card { background: rgba(31, 41, 55, 0.85); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 16px; padding: 30px; }
.sol-badge { font-size: 13px; font-weight: 800; color: #10B981; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 10px; }
.sol-title { font-size: 28px; font-weight: 800; color: #FFF; margin-bottom: 6px; }
.sol-detail { font-size: 15px; color: #9CA3AF; margin-bottom: 20px; font-family: monospace; }
.sol-stats { list-style: none; display: flex; flex-direction: column; gap: 12px; font-size: 18px; }

.summary-card { text-align: center; padding: 60px 40px; }
.summary-title { font-size: 56px; font-weight: 900; color: #FFF; margin-bottom: 30px; }
.decision-receipt { background: rgba(0, 0, 0, 0.6); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 16px; padding: 30px; max-width: 900px; margin: 0 auto 30px auto; text-align: left; }
.receipt-header { font-size: 20px; font-weight: 800; color: #10B981; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 12px; margin-bottom: 16px; }
.receipt-body { display: flex; flex-direction: column; gap: 12px; font-size: 18px; color: #E5E7EB; line-height: 1.5; }
.tech-stack-row { font-size: 17px; color: #9CA3AF; letter-spacing: 1px; }

.footer-bar { display: flex; justify-content: space-between; align-items: center; z-index: 10; border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 20px; font-size: 16px; color: #9CA3AF; }
.scene-indicator { font-weight: 700; color: #00F0FF; }
"""

def generate_scene_html(scene, index, total):
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{scene['title']}</title>
    <style>{CSS_STYLES}</style>
</head>
<body>
    <div class="header-bar">
        <div class="logo-title">
            <span>TWINFORGE</span>
            <span class="logo-pill">FALKORDB GRAPH DEMO</span>
        </div>
        <div class="header-meta">{scene['subtitle']}</div>
    </div>
    <div class="content-container">
        {scene['html']}
    </div>
    <div class="footer-bar">
        <div>TwinForge Multi-Agent Supply Chain • FalkorDB Graph Demo</div>
        <div class="scene-indicator">SCENE {index + 1} OF {total}</div>
    </div>
</body>
</html>
"""

def get_audio_duration(audio_file):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_file
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(res.stdout.strip() or 5.0)

def main():
    print("🎬 Starting TwinForge Demo Video Generation Pipeline...")
    total_scenes = len(SCENES)
    video_segments = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        for idx, scene in enumerate(SCENES):
            scene_id = scene["id"]
            print(f"\n--- Processing Scene {idx+1}/{total_scenes}: {scene['title']} ---")

            # 1. Generate & Render HTML Slide
            html_content = generate_scene_html(scene, idx, total_scenes)
            html_path = os.path.join(WORK_DIR, f"{scene_id}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            img_path = os.path.join(WORK_DIR, f"{scene_id}.png")
            page.goto(f"file://{html_path}")
            page.wait_for_timeout(300)
            page.screenshot(path=img_path)
            print(f"  📸 Captured 1080p slide: {img_path}")

            # 2. Generate Audio Voiceover via macOS TTS
            aiff_path = os.path.join(WORK_DIR, f"{scene_id}.aiff")
            wav_path = os.path.join(WORK_DIR, f"{scene_id}.wav")
            # Using Samantha voice at a smooth industrial narrative cadence
            subprocess.run(["/usr/bin/say", "-v", "Samantha", "-r", "175", "-o", aiff_path, scene["narration"]], check=True)
            subprocess.run(["/opt/homebrew/bin/ffmpeg", "-y", "-i", aiff_path, "-ar", "44100", "-ac", "2", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            dur = get_audio_duration(wav_path) + 0.8  # Add 0.8s buffer padding
            print(f"  🎙️ Voiceover generated: {dur:.1f}s")

            # 3. Create Video Segment with FFmpeg
            segment_path = os.path.join(WORK_DIR, f"{scene_id}.mp4")
            cmd = [
                "/opt/homebrew/bin/ffmpeg", "-y",
                "-loop", "1", "-i", img_path,
                "-i", wav_path,
                "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-t", str(dur),
                "-shortest",
                segment_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            video_segments.append(segment_path)
            print(f"  🎞️ Segment rendered: {segment_path}")

        browser.close()

    # 4. Concatenate All Segments into Final MP4
    print("\n📦 Concatenating video segments...")
    concat_list_path = os.path.join(WORK_DIR, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for seg in video_segments:
            f.write(f"file '{seg}'\n")

    cmd_concat = [
        "/opt/homebrew/bin/ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        OUTPUT_VIDEO
    ]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    total_dur = sum(get_audio_duration(os.path.join(WORK_DIR, f"{s['id']}.wav")) + 0.8 for s in SCENES)
    file_size_mb = os.path.getsize(OUTPUT_VIDEO) / (1024 * 1024)

    print("\n" + "="*60)
    print("🎉 VIDEO CREATION COMPLETE!")
    print(f"📁 Video Location: {OUTPUT_VIDEO}")
    print(f"⏱️ Total Duration: {total_dur:.1f} seconds (~{int(total_dur // 60)}m {int(total_dur % 60)}s)")
    print(f"💾 File Size: {file_size_mb:.2f} MB")
    print(f"🌐 Web Stream: http://localhost:8000/static/twinforge_demo.mp4")
    print("="*60)

if __name__ == "__main__":
    main()
