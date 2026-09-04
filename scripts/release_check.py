from __future__ import annotations

import argparse
import json

from backtesting.validation import summarize_pnl
from release.validation import validate_paper_ledger
from web.monitoring import monitoring_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the paper-only release path")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--fixture", action="store_true", help="run the deterministic end-to-end paper fixture")
    args = parser.parse_args()

    if args.fixture:
        from release.paper_fixture import build_paper_release_fixture
        fixture = build_paper_release_fixture(args.data_dir)
        report = {
            "release_mode": "paper-only",
            "fixture": fixture.__dict__,
            "ready": (
                fixture.ledger["valid"]
                and fixture.backtest["validated"]
                and fixture.monitoring["health"] == "ok"
                and fixture.attribution["trades"] == fixture.ledger["trades"]
            ),
        }
    else:
        ledger = validate_paper_ledger(f"{args.data_dir}/paper_trades.jsonl")
        snapshot = monitoring_snapshot(args.data_dir)
        report = {
            "release_mode": "paper-only",
            "ledger": ledger.__dict__,
            "monitoring": snapshot,
            "empty_pnl": summarize_pnl([]).__dict__,
            "ready": ledger.healthy and snapshot["health"] == "ok",
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
