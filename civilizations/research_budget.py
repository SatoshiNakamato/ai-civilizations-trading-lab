from __future__ import annotations

import json
import time
from pathlib import Path
from threading import Lock


class ResearchBudget:
    """Persistent daily allocation for the shared You.com free-search budget.

    The default policy reserves 50 searches for dedicated arbitrage research
    and 50 for every other research topic. Cache hits do not consume budget;
    failed provider calls do consume a reserved slot because the request was
    sent to the provider.
    """

    def __init__(self, path: str = "data/research_budget.json", daily_limit: int = 100,
                 arbitrage_limit: int = 50):
        self.path = Path(path)
        self.daily_limit = max(1, int(daily_limit))
        self.arbitrage_limit = min(max(0, int(arbitrage_limit)), self.daily_limit)
        self.other_limit = self.daily_limit - self.arbitrage_limit
        self._lock = Lock()
        self._state = self._load()

    def _load(self) -> dict:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def _day() -> str:
        return time.strftime("%Y-%m-%d", time.localtime())

    def _bucket(self) -> dict:
        return self._state.setdefault("days", {}).setdefault(
            self._day(), {"arbitrage": 0, "other": 0}
        )

    @staticmethod
    def category(topic: str) -> str:
        return "arbitrage" if str(topic).strip().lower() == "arb" else "other"

    def reserve(self, topic: str) -> bool:
        category = self.category(topic)
        with self._lock:
            bucket = self._bucket()
            key = category
            used = int(bucket.get(key, 0))
            limit = self.arbitrage_limit if category == "arbitrage" else self.other_limit
            if used >= limit:
                return False
            bucket[key] = used + 1
            self._save()
            return True

    def snapshot(self) -> dict:
        bucket = self._bucket()
        arb_used = int(bucket.get("arbitrage", 0))
        other_used = int(bucket.get("other", 0))
        return {
            "date": self._day(),
            "daily_limit": self.daily_limit,
            "arbitrage": {"used": arb_used, "limit": self.arbitrage_limit,
                          "remaining": max(0, self.arbitrage_limit - arb_used)},
            "other": {"used": other_used, "limit": self.other_limit,
                      "remaining": max(0, self.other_limit - other_used)},
            "total_used": arb_used + other_used,
            "total_remaining": max(0, self.daily_limit - arb_used - other_used),
            "policy": "50 arbitrage / 50 other",
        }
