"""Long-running entry point for hosted civilization workers.

The worker is deliberately dependency-light: it restores its cycle counter from
local state, runs one civilization cycle, persists a heartbeat, and repeats.
External credentials remain environment-only. Live token deployment is still
controlled by the existing Bankr integration/policy gates.
"""
from __future__ import annotations

import json
import os
import signal
import time
from pathlib import Path

from civilizations.orchestrator import CivilizationOrchestrator
from markets.end_to_end import TradingCivilizationV1


STOP = False


def _stop(_signum, _frame):
    global STOP
    STOP = True


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def main() -> int:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    data_dir = os.getenv("CIVILIZATION_DATA_DIR", "data/civilization")
    interval = max(0.25, _env_float("CIVILIZATION_CYCLE_INTERVAL", 30.0))
    count = max(1, _env_int("CIVILIZATION_AGENT_COUNT", 100))
    agents = [f"A{i:03d}" for i in range(1, count + 1)]

    Path(data_dir).mkdir(parents=True, exist_ok=True)
    state_path = Path(data_dir) / "worker_state.json"
    heartbeat_path = Path(data_dir) / "heartbeat.json"

    # The current lifecycle accepts a runtime for live arbitrage execution. A
    # hosted smoke-test starts without a market runtime, so it can stay alive
    # and exercise the durable civilization lifecycle safely.
    civilization = TradingCivilizationV1(runtime=None, agents=agents, data_dir=data_dir)
    orchestrator = CivilizationOrchestrator({"trading_civilization": civilization})

    if state_path.exists():
        try:
            saved = json.loads(state_path.read_text(encoding="utf-8"))
            civilization.cycle_count = int(saved.get("cycles", 0))
            orchestrator.state.cycles = civilization.cycle_count
        except (ValueError, OSError, json.JSONDecodeError):
            pass

    print(
        f"CIVILIZATION WORKER STARTED agents={count} interval={interval}s "
        f"data_dir={data_dir}",
        flush=True,
    )

    while not STOP:
        started = time.time()
        try:
            result = orchestrator.cycle()
            snapshot = orchestrator.snapshot()
            heartbeat = {
                "status": "running",
                "cycle": civilization.cycle_count,
                "agents": count,
                "started_at": started,
                "last_cycle_at": time.time(),
                "snapshot": snapshot,
                "result": result,
            }
            heartbeat_path.write_text(json.dumps(heartbeat, default=str), encoding="utf-8")
            state_path.write_text(
                json.dumps({"cycles": civilization.cycle_count, "updated_at": time.time()}),
                encoding="utf-8",
            )
            print(
                f"CYCLE {civilization.cycle_count} COMPLETE agents={count}",
                flush=True,
            )
        except Exception as exc:
            # Keep the supervisor alive on recoverable component errors. The
            # exception is visible in hosted logs and the next cycle retries it.
            print(f"CYCLE ERROR {type(exc).__name__}: {exc}", flush=True)
            heartbeat_path.write_text(
                json.dumps(
                    {"status": "degraded", "cycle": civilization.cycle_count, "error": str(exc)},
                    default=str,
                ),
                encoding="utf-8",
            )

        elapsed = time.time() - started
        remaining = max(0.0, interval - elapsed)
        deadline = time.monotonic() + remaining
        while not STOP and time.monotonic() < deadline:
            time.sleep(min(1.0, deadline - time.monotonic()))

    heartbeat_path.write_text(
        json.dumps({"status": "stopped", "cycle": civilization.cycle_count}),
        encoding="utf-8",
    )
    print("CIVILIZATION WORKER STOPPED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
