import asyncio
import os
import json
import subprocess
import edge_tts

SCENES = [
    {
        "id": "scene1",
        "title": "Intro & Architecture Overview",
        "text": "Welcome to TwinForge Connected Graph, an autonomous industrial digital twin and self-healing supply chain intelligence platform. Built natively on FalkorDB's high-speed property graph database, TwinForge Connected Graph monitors distributed physical plant assets, traverses multi-hop dependency networks, and deploys prescriptive agentic mitigations in real time. Notice our clean light theme interface, complete with a dark mode toggle and real-time plant telemetry."
    },
    {
        "id": "scene2",
        "title": "Connected-Graph & Blast Radius",
        "text": "In the Connected-Graph view, every physical machine is connected to its parent plant, produced parts, and downstream assemblies. When we select robotic arm A-ROB-03, also known as M7, FalkorDB instantly executes a multi-hop blast radius traversal. In milliseconds, the graph reveals that M7's bearing wear threatens part PT-4, halting production of turbine module P4 and jeopardizing high-tier customer delivery contracts."
    },
    {
        "id": "scene3",
        "title": "Command Center & FalkorDB KPIs",
        "text": "Switching over to the Command Center, operations teams get a comprehensive live overview of plant health. Every metric card displayed here—including overall equipment effectiveness, machine risk scores, and inventory shortages—is computed via real-time Cypher aggregations against FalkorDB. The hourly production chart continuously benchmarks actual output against target schedules across all manufacturing lines."
    },
    {
        "id": "scene4",
        "title": "Autonomous AI Agent Investigation",
        "text": "When risk thresholds are exceeded, our autonomous AI agent initiates an automated investigation. Operating through an MCP tool interface connected directly to FalkorDB, the agent executes Cypher queries to evaluate machine telemetry, inspect product bills of materials, and query alternate suppliers. Below, FalkorDB extracts and renders the complete evidence subgraph, providing explainable proof for every diagnostic step."
    },
    {
        "id": "scene5",
        "title": "Multi-Echelon Supply Chain Simulator",
        "text": "In the Multi-Echelon Simulator, supply chain engineers can simulate disruptions before they impact production. FalkorDB's property graph links plants, regional warehouses, and global suppliers with dynamic transit times and expedite multipliers. When machine M7 trips, the simulator compares lead times from alternate suppliers against backup capacity at our sister facility in Leipzig."
    },
    {
        "id": "scene6",
        "title": "Prescriptive Approvals & Graph Lineage",
        "text": "Governance and human oversight are integral to TwinForge Connected Graph. In the Approvals view, the agent's prescriptive mitigation recommendation is presented with clear financial and operational tradeoffs. When the operator approves the plan, FalkorDB executes a write transaction, creating a persistent Decision node linked via BASED_ON relationships directly to the supporting evidence nodes for immutable compliance."
    },
    {
        "id": "scene7",
        "title": "Audit Trail, Control Room & Integrations",
        "text": "Finally, the Audit Trail records every automated and human decision with cryptographic verification. The Plant Control Room provides direct operational oversight over active lines. And in the Integrations panel, you can verify our live FalkorDB instance on port 6379 with graph name supply chain. TwinForge Connected Graph demonstrates the unmatched speed and intelligence of graph-native AI agents. Thank you for watching."
    }
]

os.makedirs("video_build/audio", exist_ok=True)

# en-US-ChristopherNeural is a realistic, warm, studio-quality human voice
VOICE = "en-US-ChristopherNeural"
RATE = "-2%"

async def generate_scene_audio(scene):
    mp3_path = f"video_build/audio/{scene['id']}.mp3"
    wav_path = f"video_build/audio/{scene['id']}.wav"
    
    communicate = edge_tts.Communicate(scene["text"], VOICE, rate=RATE)
    await communicate.save(mp3_path)
    
    # Convert to standard 44.1kHz stereo WAV
    cmd_ffmpeg = ["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "2", wav_path]
    subprocess.run(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    # Probe duration
    cmd_probe = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", wav_path]
    res = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
    dur = float(json.loads(res.stdout)["format"]["duration"])
    scene["duration"] = dur
    print(f"[{scene['id']}] {scene['title']}: {dur:.2f}s (Natural Neural Voice)")
    return dur

async def main():
    total_duration = 0.0
    for scene in SCENES:
        dur = await generate_scene_audio(scene)
        total_duration += dur

    print(f"\nTotal Voiceover Duration: {total_duration:.2f}s (~{total_duration/60:.2f} minutes)")
    with open("video_build/scenes.json", "w") as f:
        json.dump(SCENES, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
