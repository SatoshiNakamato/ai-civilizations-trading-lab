from __future__ import annotations

import os
import time

from execution.ccxt_adapter import CcxtExchangeAdapter
from execution.engine import LiveExecutionEngine
from execution.live_runtime import LiveTradingRuntime


def build_live_runtime():
    if os.getenv("LIVE_TRADING") != "1":
        raise RuntimeError("LIVE_TRADING=1 is required to start the live worker")
    adapter = CcxtExchangeAdapter()
    engine = LiveExecutionEngine(adapter)
    return LiveTradingRuntime(engine)


def run_forever(interval=30):
    runtime = build_live_runtime()
    print(f"LIVE TRADING WORKER STARTED exchange={runtime.engine.adapter.exchange_id} interval={interval}s", flush=True)
    while True:
        # Research-to-intent orchestration is intentionally supplied by the
        # civilization runtime; this worker owns the live execution/reconcile loop.
        try:
            reconciled = runtime.engine.reconcile_open_orders()
            print(f"LIVE RECONCILE orders={len(reconciled)}", flush=True)
        except Exception as exc:
            print(f"LIVE RECONCILE ERROR {type(exc).__name__}: {exc}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    run_forever(float(os.getenv("LIVE_INTERVAL", "30")))
