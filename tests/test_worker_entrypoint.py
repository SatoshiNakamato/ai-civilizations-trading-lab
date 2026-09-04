import json
import os
import signal
import subprocess
import sys
import time


def test_worker_module_smoke(tmp_path):
    env = os.environ.copy()
    env["CIVILIZATION_DATA_DIR"] = str(tmp_path)
    env["CIVILIZATION_CYCLE_INTERVAL"] = "0.25"
    env["CIVILIZATION_AGENT_COUNT"] = "4"

    proc = subprocess.Popen(
        [sys.executable, "-m", "simulation.run"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    try:
        deadline = time.time() + 8
        heartbeat = tmp_path / "heartbeat.json"
        while time.time() < deadline and not heartbeat.exists():
            time.sleep(0.05)
        assert heartbeat.exists()
        payload = json.loads(heartbeat.read_text())
        assert payload["status"] in {"running", "degraded"}
        assert payload["agents"] == 4
        assert payload["cycle"] >= 1
        assert proc.poll() is None
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
