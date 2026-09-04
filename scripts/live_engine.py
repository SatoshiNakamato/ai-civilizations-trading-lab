from __future__ import annotations

import os
import time

from civilizations.autonomous_research import AutonomousResearchEngine
from markets.live_controller import LiveTradingController
from markets.live_execution import LiveExecutionEngine, LiveExecutionError


def main():
    if os.getenv("LIVE_TRADING") != "1":
        raise SystemExit("LIVE_TRADING=1 is required; this worker never falls back to paper trading")

    data_dir = os.getenv("LIVE_DATA_DIR", "data/live")
    interval = float(os.getenv("LIVE_INTERVAL_SECONDS", "30"))
    agents = [f"A{i:03d}" for i in range(1, 101)]
    research = AutonomousResearchEngine()
    executor = LiveExecutionEngine.from_env(f"{data_dir}/orders.jsonl")
    controller = LiveTradingController(executor)
    print("LIVE AUTONOMOUS TRADING ENGINE STARTED", flush=True)
    print(executor.preflight()["exchange"], flush=True)

    cycle = 0
    while True:
        cycle += 1
        try:
            opportunities = research.cycle(agents, cycle)
            selected = controller.select(opportunities)
            if selected is None:
                print(f"CYCLE {cycle} NO LIVE SIGNAL", flush=True)
            else:
                event = controller.execute_top(opportunities)
                print(f"CYCLE {cycle} LIVE ORDER status={event['status']} order={event['order'].get('id')}", flush=True)
        except LiveExecutionError as exc:
            print(f"CYCLE {cycle} LIVE EXECUTION HALTED: {exc}", flush=True)
        except Exception as exc:
            print(f"CYCLE {cycle} ERROR: {type(exc).__name__}: {exc}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
