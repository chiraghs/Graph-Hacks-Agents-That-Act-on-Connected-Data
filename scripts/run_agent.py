"""scripts/run_agent.py - Runs the autonomous agent investigation loop in the terminal."""

import sys
import json
import asyncio
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.agent.runner import stream_investigation


async def main():
    print("Running Supply Chain Agent in terminal via core.agent.runner...")
    async for event in stream_investigation():
        evt_type = event["event"]
        evt_data = event["data"]
        if evt_type == "tool_call":
            print(f"\n[TOOL CALL] -> {evt_data['tool']}({json.dumps(evt_data['input'])})")
        elif evt_type == "tool_result":
            tool = evt_data["tool"]
            res = evt_data["result"]
            lat = evt_data.get("latency_ms", "N/A")
            summary = str(res)[:120] + "..." if len(str(res)) > 120 else str(res)
            print(f"[TOOL RESULT] <- {tool} ({lat}ms): {summary}")
        elif evt_type == "agent_report":
            print("\n" + "=" * 60)
            print("FINAL AGENT REPORT:")
            print("=" * 60)
            print(f"Summary: {evt_data['summary']}")
            print("\nACTIONS TAKEN:")
            for a in evt_data["actions_taken"]:
                print(f"  • [{a['decision_id']}] {a['action_type']} on {a['machine_id']}: {a['reason']}")
            print("\nACTIONS CLEARED (NO ACTION):")
            for c in evt_data["actions_cleared"]:
                print(f"  • {c['machine_id']} [{c['status']}]: {c['reason']}")


if __name__ == "__main__":
    asyncio.run(main())
