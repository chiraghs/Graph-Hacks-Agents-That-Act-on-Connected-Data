"""scripts/capture_screenshots.py - Captures crisp, 1080p screenshots of the live TwinForge UI.
"""

import time
import os
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = os.path.abspath("assets/screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

BASE_URL = "http://localhost:8000"

print(f"Capturing screenshots from {BASE_URL} into {SCREENSHOTS_DIR}...")

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        headless=True
    )
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        device_scale_factor=1.5  # Crisp retina quality
    )
    page = context.new_page()
    page.on("dialog", lambda dialog: dialog.accept())

    # 1. Connected-Graph & Digital Twin Studio
    print("Capturing 01_connected_graph_twin.png...")
    page.goto(f"{BASE_URL}/twin")
    page.wait_for_load_state("networkidle")
    time.sleep(3.0)
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_connected_graph_twin.png"))

    # 2. Blast Radius Drawer (Select M7)
    print("Capturing 02_blast_radius_drawer.png...")
    page.evaluate("selectAsset('A-ROB-03');")
    time.sleep(3.0)
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_blast_radius_drawer.png"))

    # Close drawer
    page.evaluate("const d = document.getElementById('drawer-asset-panel'); if (d) d.classList.add('hidden');")
    time.sleep(1.0)

    # 3. Graph Copilot Modal
    print("Capturing 03_copilot_modal.png...")
    page.evaluate("openCopilotModal();")
    time.sleep(1.5)
    page.click("#copilot-user-input")
    page.keyboard.type("If Machine M7 in Detroit fails, what is the inventory shortfall and hourly penalty for HyperDrive Electric Motors order of P4 Smart Turbines?", delay=5)
    time.sleep(0.5)
    page.click("#copilot-submit-btn")
    time.sleep(5.0)
    page.evaluate("const ct = document.getElementById('copilot-chat-thread'); if (ct) ct.scrollTop = ct.scrollHeight;")
    time.sleep(1.5)
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_copilot_modal.png"))

    # Close Copilot
    page.evaluate("closeCopilotModal();")
    time.sleep(1.0)

    # 4. Command Center KPIs
    print("Capturing 04_command_center.png...")
    page.evaluate("navigatePage('dashboard');")
    page.wait_for_load_state("networkidle")
    time.sleep(3.0)
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_command_center.png"))

    # 5. Autonomous Agent Investigation Console
    print("Capturing 05_agent_investigation.png...")
    page.evaluate("navigatePage('agents');")
    page.wait_for_load_state("networkidle")
    time.sleep(2.0)
    # Trigger live agent run
    page.click("#btn-run-agent")
    time.sleep(10.0)  # Wait for investigation and evidence subgraph
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_agent_investigation.png"))

    # 6. Supply Chain Simulator
    print("Capturing 06_supply_chain_simulator.png...")
    page.evaluate("navigatePage('simulator');")
    page.wait_for_load_state("networkidle")
    time.sleep(3.0)
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "06_supply_chain_simulator.png"))

    # 7. Prescriptive Approvals
    print("Capturing 07_prescriptive_approvals.png...")
    page.evaluate("navigatePage('approvals');")
    page.wait_for_load_state("networkidle")
    time.sleep(3.0)
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "07_prescriptive_approvals.png"))

    # 8. Cryptographic Audit Trail
    print("Capturing 08_audit_trail.png...")
    page.evaluate("navigatePage('audit');")
    page.wait_for_load_state("networkidle")
    time.sleep(3.0)
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "08_audit_trail.png"))

    # 9. Predictive Maintenance Studio
    print("Capturing 09_predictive_maintenance_studio.png...")
    page.evaluate("navigatePage('pdm');")
    page.wait_for_load_state("networkidle")
    time.sleep(3.5)
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "09_predictive_maintenance_studio.png"))

    # 10. Demand Forecasting Studio
    print("Capturing 10_demand_forecasting_studio.png...")
    page.evaluate("navigatePage('forecasting');")
    page.wait_for_load_state("networkidle")
    time.sleep(3.5)
    page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "10_demand_forecasting_studio.png"))

    context.close()
    browser.close()

print("All screenshots successfully captured!")
