from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json


def _tail_jsonl(path: str, limit: int = 100) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def monitoring_snapshot(data_dir: str = "data") -> dict:
    root = Path(data_dir)
    audit = _tail_jsonl(str(root / "audit.jsonl"))
    paper = _tail_jsonl(str(root / "paper_trades.jsonl"))
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "health": "ok",
        "paper": {
            "trades_seen": len(paper),
            "last_trade": paper[-1] if paper else None,
        },
        "audit": {
            "events_seen": len(audit),
            "last_event": audit[-1] if audit else None,
        },
        "live_execution": "disabled-by-default",
    }


def render_dashboard(snapshot: dict) -> str:
    """Return dependency-free HTML suitable for Termux/local hosting."""
    payload = json.dumps(snapshot, separators=(",", ":"))
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>AI Civilization Trading Lab</title><style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}pre{{white-space:pre-wrap;background:#f5f5f5;padding:1rem;border-radius:8px}}</style></head><body><h1>AI Civilization Trading Lab</h1><p>Monitoring snapshot: <strong>{snapshot['health']}</strong></p><pre id='data'>{payload}</pre></body></html>"""
