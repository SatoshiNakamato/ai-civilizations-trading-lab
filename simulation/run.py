"""Persistent hosted worker entry point for the trading civilization."""
from __future__ import annotations

import json
import os
import signal
import time
from pathlib import Path

STOP = False


def _stop(_signum, _frame):
    global STOP
    STOP = True
    # Interrupt an in-flight Python operation so a hosted worker does not wait
    # indefinitely for a slow network/research call before honoring shutdown.
    raise KeyboardInterrupt("worker shutdown requested")


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, default=str), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    global STOP
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    data_dir = Path(os.getenv("CIVILIZATION_DATA_DIR", "data/civilization"))
    interval = max(0.1, _float_env("CIVILIZATION_CYCLE_INTERVAL", 30.0))
    count = max(1, _int_env("CIVILIZATION_AGENT_COUNT", 100))
    agents = [f"A{i:03d}" for i in range(1, count + 1)]
    state_path = data_dir / "worker_state.json"
    heartbeat_path = data_dir / "heartbeat.json"
    data_dir.mkdir(parents=True, exist_ok=True)

    orchestrator = None
    civilization = None
    startup_error = None
    try:
        from civilizations.orchestrator import CivilizationOrchestrator
        from markets.end_to_end import TradingCivilizationV1
        civilization = TradingCivilizationV1(runtime=None, agents=agents, data_dir=str(data_dir))
        orchestrator = CivilizationOrchestrator({"trading_civilization": civilization})
    except BaseException as exc:
        startup_error = f"{type(exc).__name__}: {exc}"

    cycle = 0
    try:
        if state_path.exists():
            cycle = int(json.loads(state_path.read_text(encoding="utf-8")).get("cycles", 0))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        cycle = 0

    if civilization is not None:
        civilization.cycle_count = cycle
    if orchestrator is not None:
        orchestrator.state.cycles = cycle

    print(f"CIVILIZATION WORKER STARTED agents={count} interval={interval}s data_dir={data_dir}", flush=True)
    if startup_error:
        print(f"STARTUP DEGRADED {startup_error}", flush=True)

    _write_json(heartbeat_path, {
        "status": "degraded" if startup_error else "starting",
        "cycle": cycle,
        "agents": count,
        "last_cycle_at": None,
        "elapsed": 0.0,
        "error": startup_error,
        "result": None,
    })

    while not STOP:
        started = time.time()
        cycle += 1
        error = startup_error
        result = None
        try:
            if orchestrator is None:
                from civilizations.orchestrator import CivilizationOrchestrator
                from markets.end_to_end import TradingCivilizationV1
                civilization = TradingCivilizationV1(runtime=None, agents=agents, data_dir=str(data_dir))
                civilization.cycle_count = cycle - 1
                orchestrator = CivilizationOrchestrator({"trading_civilization": civilization})
                orchestrator.state.cycles = cycle - 1
            _write_json(heartbeat_path, {
                "status": "running",
                "cycle": cycle,
                "agents": count,
                "last_cycle_at": time.time(),
                "elapsed": 0.0,
                "error": None,
                "result": None,
            })
            result = orchestrator.cycle()
            cycle = civilization.cycle_count
            startup_error = None
            error = None
        except KeyboardInterrupt:
            if STOP:
                break
            error = "KeyboardInterrupt"
        except BaseException as exc:
            error = f"{type(exc).__name__}: {exc}"
            print(f"CYCLE ERROR cycle={cycle} {error}", flush=True)

        if STOP:
            break
        try:
            _write_json(heartbeat_path, {
                "status": "degraded" if error else "running",
                "cycle": cycle,
                "agents": count,
                "last_cycle_at": time.time(),
                "elapsed": time.time() - started,
                "error": error,
                "result": result,
            })
            _write_json(state_path, {"cycles": cycle, "updated_at": time.time()})
        except BaseException as exc:
            print(f"STATE ERROR {type(exc).__name__}: {exc}", flush=True)

        print(f"CYCLE {cycle} COMPLETE status={'degraded' if error else 'ok'} agents={count}", flush=True)
        deadline = time.monotonic() + max(0.0, interval - (time.time() - started))
        while not STOP and time.monotonic() < deadline:
            time.sleep(min(1.0, max(0.01, deadline - time.monotonic())))

    try:
        _write_json(heartbeat_path, {"status": "stopped", "cycle": cycle, "stopped_at": time.time()})
    except BaseException:
        pass
    print(f"CIVILIZATION WORKER STOPPED cycle={cycle}", flush=True)
    return 0


if __name__ == "__main__":
    main()
