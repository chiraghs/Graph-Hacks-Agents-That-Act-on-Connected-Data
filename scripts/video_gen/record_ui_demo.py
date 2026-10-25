#!/usr/bin/env python3
"""scripts/video_gen/record_ui_demo.py
Records a real, live UI demonstration video of the TwinForge Connected Graph platform.
Uses Playwright to interact with http://localhost:8000, typing queries into the live
Copilot modal, inspecting machine M7, and navigating the digital twin studio.
Synchronizes the browser video with studio voiceover narration using ffmpeg.
"""

import os
import subprocess
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORK_DIR = os.path.join(BASE_DIR, "scripts", "video_gen", "ui_record_temp")
OUTPUT_VIDEO = os.path.join(BASE_DIR, "static", "twinforge_demo.mp4")
BACKUP_VIDEO = os.path.join(BASE_DIR, "static", "twinforge_ui_demo.mp4")

os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)

# Narration segments synchronized to UI timeline
NARRATION_SCRIPTS = [
    {
        "id": "part1_intro_twin",
        "text": "Welcome to TwinForge, an autonomous industrial digital twin powered by FalkorDB. Here in the Twin Studio, we visualize over 3,700 connected nodes and 6,000 multi-hop relationships across our Apex Detroit and London manufacturing facilities.",
    },
    {
        "id": "part2_copilot_hi",
        "text": "Let's open the TwinForge Graph Copilot. We start with a natural conversational greeting. The Copilot recognizes the intent conversationally, welcomes us, and suggests exploration prompts without running wasteful database queries.",
    },
    {
        "id": "part3_copilot_hyperdrive",
        "text": "Now, let's ask a complex operational question: If Machine M7 in Detroit fails, what is the inventory shortfall and hourly penalty for HyperDrive Electric Motors order of P4 Smart Turbines? In under 40 milliseconds, FalkorDB executes a 5-hop Cypher traversal. It reveals a 150-unit buffer shortfall and a 25,000 dollar per hour delay penalty clause on HyperDrive's critical purchase order.",
    },
    {
        "id": "part4_copilot_spares",
        "text": "Next, we check emergency logistics: What is the status of the emergency spare spindle for M7? FalkorDB instantly reports zero stock locally in Detroit, but identifies two direct-drive units at our Munich Mechatronics Hub ready for 8.5-hour chartered air transit.",
    },
    {
        "id": "part5_navigation_audit",
        "text": "Closing the Copilot, we examine the Operations Dashboard and autonomous agent control room. Every remediation action and standby retooling assignment is recorded as an immutable decision node in FalkorDB, ensuring auditability and complete operational resilience.",
    }
]

def generate_voiceover():
    """Generates audio files for each section using macOS TTS."""
    audio_files = []
    for item in NARRATION_SCRIPTS:
        sec_id = item["id"]
        aiff_path = os.path.join(WORK_DIR, f"{sec_id}.aiff")
        wav_path = os.path.join(WORK_DIR, f"{sec_id}.wav")
        # Generate with clear speech
        subprocess.run(["/usr/bin/say", "-v", "Samantha", "-r", "175", "-o", aiff_path, item["text"]], check=True)
        subprocess.run(["/opt/homebrew/bin/ffmpeg", "-y", "-i", aiff_path, "-ar", "44100", "-ac", "2", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Get duration
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", wav_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dur = float(res.stdout.strip() or 10.0)
        audio_files.append({"id": sec_id, "wav": wav_path, "duration": dur})
        print(f"🎙️ Voiceover generated for {sec_id}: {dur:.1f}s")
    return audio_files

def type_text(page, selector, text, delay=35):
    """Types text character by character like a human operator."""
    page.click(selector)
    for char in text:
        page.keyboard.type(char)
        page.wait_for_timeout(delay)

def record_ui_session(durations):
    """Executes live UI actions synchronized with narration durations."""
    print("🎬 Launching Chromium for UI interaction recording...")
    raw_video_dir = os.path.join(WORK_DIR, "browser_rec")
    os.makedirs(raw_video_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=raw_video_dir,
            record_video_size={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        # Part 1: Intro & Twin Studio (Topology & Floor Plan)
        print("  ▶️ Part 1: Digital Twin Studio & Topology View...")
        page.goto("http://localhost:8000")
        page.wait_for_timeout(3000)
        
        # Smooth pan / view switch
        page.evaluate("if (typeof setTwinView === 'function') setTwinView('floor')")
        page.wait_for_timeout(3500)
        page.evaluate("if (typeof setTwinView === 'function') setTwinView('topology')")
        page.wait_for_timeout(max(1000, int((durations[0]["duration"] - 6.5) * 1000)))

        # Part 2: Open Copilot & Type "Hi"
        print("  ▶️ Part 2: Opening Copilot & Conversational Greeting...")
        page.evaluate("openCopilotModal()")
        page.wait_for_timeout(1500)
        type_text(page, "#copilot-user-input", "Hi", delay=80)
        page.wait_for_timeout(800)
        page.click("#copilot-submit-btn")
        # Wait for conversational reply
        page.wait_for_timeout(max(2000, int((durations[1]["duration"] - 4.5) * 1000)))

        # Part 3: Operational Question on M7 & HyperDrive
        print("  ▶️ Part 3: Operational Inquiry (M7 failure, shortfall & penalty)...")
        q_m7 = "If Machine M7 in Detroit fails, what is the inventory shortfall and hourly penalty for HyperDrive Electric Motors order of P4 Smart Turbines?"
        type_text(page, "#copilot-user-input", q_m7, delay=25)
        page.wait_for_timeout(600)
        page.click("#copilot-submit-btn")
        # Wait for Cypher execution and card rendering
        page.wait_for_timeout(max(3000, int((durations[2]["duration"] - 7.0) * 1000)))

        # Part 4: Emergency Spare Logistics
        print("  ▶️ Part 4: Emergency Spares Query...")
        q_spare = "What is the status of the emergency spare spindle for M7?"
        type_text(page, "#copilot-user-input", q_spare, delay=28)
        page.wait_for_timeout(600)
        page.click("#copilot-submit-btn")
        page.wait_for_timeout(max(3000, int((durations[3]["duration"] - 5.5) * 1000)))

        # Part 5: Close Copilot & Navigate Dashboard, Agents & Audit
        print("  ▶️ Part 5: Navigation (Dashboard, Agents, Audit Trail)...")
        page.evaluate("closeCopilotModal()")
        page.wait_for_timeout(1500)
        page.evaluate("navigatePage('dashboard')")
        page.wait_for_timeout(3500)
        page.evaluate("navigatePage('agents')")
        page.wait_for_timeout(3500)
        page.evaluate("navigatePage('audit')")
        page.wait_for_timeout(max(2000, int((durations[4]["duration"] - 8.5) * 1000)))
        page.wait_for_timeout(2000)

        # Close page and context to finalize video
        page.close()
        context.close()
        browser.close()

    # Find the recorded webm file
    recorded_files = [os.path.join(raw_video_dir, f) for f in os.listdir(raw_video_dir) if f.endswith(".webm")]
    if not recorded_files:
        raise RuntimeError("No recorded webm video found from Playwright!")
    
    print(f"🎥 Browser UI recorded successfully: {recorded_files[0]}")
    return recorded_files[0]

def compile_final_video(recorded_webm, audio_files):
    """Combines browser recording with combined narration audio."""
    print("📦 Combining narration tracks and browser recording with FFmpeg...")
    
    # 1. Concatenate all audio tracks
    concat_audio_txt = os.path.join(WORK_DIR, "audio_concat.txt")
    with open(concat_audio_txt, "w") as f:
        for item in audio_files:
            f.write(f"file '{item['wav']}'\n")

    combined_audio = os.path.join(WORK_DIR, "combined_narration.wav")
    subprocess.run([
        "/opt/homebrew/bin/ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_audio_txt,
        "-c", "copy",
        combined_audio
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 2. Get durations
    cmd_a = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", combined_audio]
    audio_dur = float(subprocess.run(cmd_a, stdout=subprocess.PIPE, text=True).stdout.strip() or 60.0)

    cmd_v = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", recorded_webm]
    video_dur = float(subprocess.run(cmd_v, stdout=subprocess.PIPE, text=True).stdout.strip() or 60.0)

    print(f"⏱️ Video track duration: {video_dur:.1f}s | Narration duration: {audio_dur:.1f}s")

    # 3. Mux video and audio into output MP4
    cmd_mux = [
        "/opt/homebrew/bin/ffmpeg", "-y",
        "-i", recorded_webm,
        "-i", combined_audio,
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        OUTPUT_VIDEO
    ]
    subprocess.run(cmd_mux, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    # Also save backup copy
    subprocess.run(["cp", OUTPUT_VIDEO, BACKUP_VIDEO], check=True)

    size_mb = os.path.getsize(OUTPUT_VIDEO) / (1024 * 1024)
    print("\n" + "="*60)
    print("🎉 REAL UI DEMO VIDEO RECORDED & COMPILED!")
    print(f"📁 Video Location: {OUTPUT_VIDEO}")
    print(f"💾 File Size: {size_mb:.2f} MB")
    print(f"⏱️ Duration: {min(video_dur, audio_dur):.1f} seconds")
    print(f"🌐 Stream in Browser: http://localhost:8000/static/twinforge_demo.mp4")
    print("="*60)

def main():
    print("🚀 Starting TwinForge Real UI Screen Recording Pipeline...")
    audio_files = generate_voiceover()
    recorded_webm = record_ui_session(audio_files)
    compile_final_video(recorded_webm, audio_files)

if __name__ == "__main__":
    main()
