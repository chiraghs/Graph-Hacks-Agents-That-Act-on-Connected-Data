import json
import time
import os
import glob
import subprocess
from playwright.sync_api import sync_playwright

with open("video_build/timeline.json", "r") as f:
    meta = json.load(f)

total_target_sec = meta["total_duration"] + 1.0  # tiny padding at the very end
scenes = meta["scenes"]

raw_video_dir = os.path.abspath("video_build/raw_video")
os.makedirs(raw_video_dir, exist_ok=True)
for old in glob.glob(f"{raw_video_dir}/*"):
    try:
        os.remove(old)
    except:
        pass

print(f"Starting synchronized browser tour (Target duration: {total_target_sec:.1f}s)...")

start_time = None

def get_elapsed():
    return time.time() - start_time

def wait_until(target_sec):
    remaining = target_sec - get_elapsed()
    if remaining > 0:
        time.sleep(remaining)

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        headless=True
    )
    context = browser.new_context(
        record_video_dir=raw_video_dir,
        record_video_size={"width": 1920, "height": 1080},
        viewport={"width": 1920, "height": 1080}
    )
    page = context.new_page()
    page.on("dialog", lambda dialog: dialog.accept())

    # Navigate to initial page
    page.goto("http://localhost:8000/connected-graph")
    page.wait_for_load_state("networkidle")
    time.sleep(1.0)

    start_time = time.time()

    # -------------------------------------------------------------
    # SCENE 1: Intro & Architecture Overview (0.0s -> ~30.2s)
    # -------------------------------------------------------------
    s1 = scenes[0]
    print(f"Executing {s1['id']}: {s1['title']} ({s1['start']:.1f}s - {s1['end']:.1f}s)")
    
    # Hover over topology
    page.mouse.move(600, 450)
    time.sleep(3.0)
    page.mouse.move(950, 480)
    time.sleep(3.0)
    
    # Switch to Dark theme to showcase UI elegance
    wait_until(s1['start'] + 10.0)
    page.click("#btn-theme-toggle")
    time.sleep(4.0)
    page.mouse.move(800, 400)
    time.sleep(2.0)
    # Switch back to Light theme
    page.click("#btn-theme-toggle")
    time.sleep(2.0)
    
    # Zoom slightly or pan
    page.evaluate("if (typeof zoomCanvas === 'function') zoomCanvas(1.05);")
    wait_until(s1['end'])

    # -------------------------------------------------------------
    # SCENE 2: Connected-Graph & Blast Radius (30.2s -> ~62.2s)
    # -------------------------------------------------------------
    s2 = scenes[1]
    print(f"Executing {s2['id']}: {s2['title']} ({s2['start']:.1f}s - {s2['end']:.1f}s)")
    
    # Click Robotic Arm A-ROB-03 (M7)
    page.evaluate("selectAsset('A-ROB-03');")
    time.sleep(2.5)
    
    # Drawer is open, scroll down to multi-hop FalkorDB links
    page.mouse.move(1600, 350)
    time.sleep(2.0)
    page.evaluate("const d = document.getElementById('drawer-asset-panel'); if (d) d.scrollBy({top: 300, behavior: 'smooth'});")
    time.sleep(4.0)
    page.mouse.move(1650, 520)
    time.sleep(5.0)
    page.mouse.move(1650, 680)
    time.sleep(5.0)
    wait_until(s2['end'])

    # -------------------------------------------------------------
    # SCENE 3: Command Center & FalkorDB KPIs (62.2s -> ~90.2s)
    # -------------------------------------------------------------
    s3 = scenes[2]
    print(f"Executing {s3['id']}: {s3['title']} ({s3['start']:.1f}s - {s3['end']:.1f}s)")
    
    page.evaluate("navigatePage('dashboard');")
    time.sleep(2.0)
    
    # Scroll through KPI cards
    page.mouse.wheel(0, 300)
    time.sleep(4.0)
    page.mouse.move(450, 220)
    time.sleep(3.0)
    page.mouse.move(900, 220)
    time.sleep(3.0)
    
    # Scroll to production chart
    page.mouse.wheel(0, 350)
    time.sleep(4.0)
    page.mouse.move(600, 650)
    time.sleep(4.0)
    wait_until(s3['end'])

    # -------------------------------------------------------------
    # SCENE 4: Autonomous AI Agent Investigation
    # -------------------------------------------------------------
    s4 = scenes[3]
    print(f"Executing {s4['id']}: {s4['title']} ({s4['start']:.1f}s - {s4['end']:.1f}s)")
    
    page.evaluate("navigatePage('agents');")
    time.sleep(1.5)
    
    # Trigger Investigation SSE stream
    page.click("#btn-run-agent")
    time.sleep(2.0)
    
    # Follow real-time stream logs inside agent-logs-container
    page.mouse.move(500, 420)
    time.sleep(6.0)
    page.evaluate("const l = document.getElementById('agent-logs-container'); if (l) l.scrollTop = l.scrollHeight / 2;")
    time.sleep(5.0)
    page.evaluate("const l = document.getElementById('agent-logs-container'); if (l) l.scrollTop = l.scrollHeight;")
    time.sleep(5.0)
    
    # Hover over the Evidence Subgraph on the right
    page.mouse.move(1200, 420)
    time.sleep(5.0)
    wait_until(s4['end'])

    # -------------------------------------------------------------
    # SCENE 5: Multi-Echelon Supply Chain Simulator (119.7s -> ~146.7s)
    # -------------------------------------------------------------
    s5 = scenes[4]
    print(f"Executing {s5['id']}: {s5['title']} ({s5['start']:.1f}s - {s5['end']:.1f}s)")
    
    page.evaluate("navigatePage('simulator');")
    time.sleep(2.0)
    page.mouse.wheel(0, 250)
    time.sleep(4.0)
    page.mouse.move(650, 450)
    time.sleep(4.0)
    page.mouse.wheel(0, 300)
    time.sleep(5.0)
    page.mouse.move(1100, 600)
    time.sleep(4.0)
    wait_until(s5['end'])

    # -------------------------------------------------------------
    # SCENE 6: Prescriptive Approvals & Graph Lineage (146.7s -> ~172.6s)
    # -------------------------------------------------------------
    s6 = scenes[5]
    print(f"Executing {s6['id']}: {s6['title']} ({s6['start']:.1f}s - {s6['end']:.1f}s)")
    
    page.evaluate("navigatePage('approvals');")
    time.sleep(2.0)
    page.mouse.wheel(0, 200)
    time.sleep(4.0)
    page.mouse.move(800, 350)
    time.sleep(3.0)
    
    # Click approve mitigation plan
    page.evaluate("approvePrescription('REROUTE_MAINTAIN');")
    time.sleep(4.0)
    page.mouse.move(800, 500)
    time.sleep(4.0)
    wait_until(s6['end'])

    # -------------------------------------------------------------
    # SCENE 7: Audit Trail, Integrations & Hero Finale (172.6s -> ~201s)
    # -------------------------------------------------------------
    s7 = scenes[6]
    print(f"Executing {s7['id']}: {s7['title']} ({s7['start']:.1f}s - {s7['end']:.1f}s)")
    
    # 1. Audit Trail
    page.evaluate("navigatePage('audit');")
    time.sleep(3.0)
    page.mouse.wheel(0, 300)
    time.sleep(5.0)
    
    # 2. Integrations (FalkorDB host, port, graph, TLS)
    page.evaluate("navigatePage('integrations');")
    time.sleep(3.0)
    page.mouse.move(600, 350)
    time.sleep(4.0)
    page.mouse.move(600, 500)
    time.sleep(4.0)

    # 3. Return to Connected-Graph for finale
    page.evaluate("navigatePage('twin');")
    time.sleep(2.0)
    page.mouse.move(800, 450)
    time.sleep(2.0)
    
    wait_until(total_target_sec)

    print(f"Browser tour finished in {get_elapsed():.2f}s!")
    context.close()
    browser.close()

# Identify recorded video file
recorded_files = glob.glob(f"{raw_video_dir}/*.webm")
if not recorded_files:
    raise RuntimeError("No recorded video found in raw_video dir!")

raw_webm = recorded_files[0]
print(f"Recorded raw WebM: {raw_webm}")
