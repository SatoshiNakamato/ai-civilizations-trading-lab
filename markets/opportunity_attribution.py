from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class Attribution:
    opportunity_id: str
    agent: str
    category: str
    net_pnl: float
    notional: float
    confidence: float = 0.0


def attribute(records: list[Attribution]) -> dict:
    def group(key: str) -> dict:
        buckets = defaultdict(list)
        for row in records:
            buckets[getattr(row, key)].append(row)
        return {
            name: {
                "trades": len(rows),
                "net_pnl": round(sum(r.net_pnl for r in rows), 8),
                "notional": round(sum(r.notional for r in rows), 8),
                "win_rate": round(sum(r.net_pnl > 0 for r in rows) / len(rows), 4),
                "avg_confidence": round(sum(r.confidence for r in rows) / len(rows), 4),
            }
            for name, rows in sorted(buckets.items())
        }

    return {
        "by_opportunity": group("opportunity_id"),
        "by_agent": group("agent"),
        "by_category": group("category"),
        "total_pnl": round(sum(r.net_pnl for r in records), 8),
        "trades": len(records),
    }
