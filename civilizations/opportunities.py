from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass
class Opportunity:
    opportunity_id: str
    category: str
    asset: str
    summary: str
    confidence: float
    risk: float
    gross_edge: float = 0.0
    fees: float = 0.0
    slippage: float = 0.0
    liquidity: float = 0.0
    sources: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    buy_venue: str = ""
    sell_venue: str = ""
    buy_price: float = 0.0
    sell_price: float = 0.0
    status: str = "candidate"
    score: float = 0.0
    created_at: float = field(default_factory=time.time)
    validated_at: float = 0.0
    rejection_reason: str = ""
    observed_at: float = 0.0
    quantity: float = 0.0
    notional_usd: float = 0.0
    buy_depth: float = 0.0
    sell_depth: float = 0.0
    executable: bool = False
    verification: str = ""

    @property
    def net_edge(self) -> float:
        return self.gross_edge - self.fees - self.slippage


class OpportunityEngine:
    """Discover, validate, score, deduplicate and audit research opportunities.

    This engine produces research candidates only. It never executes trades.
    """

    def __init__(self, audit_path: str = "data/opportunity_audit.jsonl", cooldown_seconds: int = 900):
        self.audit_path = Path(audit_path)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.cooldown_seconds = max(0, int(cooldown_seconds))
        self.seen: dict[str, float] = {}
        self.opportunities: dict[str, Opportunity] = {}
        self.stats = {"discovered": 0, "validated": 0, "rejected": 0, "deduplicated": 0, "alerts": 0}

    @staticmethod
    def _key(category: str, asset: str, summary: str, buy: str = "", sell: str = "") -> str:
        text = "|".join(" ".join(x.lower().split()) for x in (category, asset, summary, buy, sell))
        return hashlib.sha256(text.encode()).hexdigest()[:20]

    def discover(self, opportunity: Opportunity) -> Opportunity | None:
        self.stats["discovered"] += 1
        key = opportunity.opportunity_id or self._key(
            opportunity.category, opportunity.asset, opportunity.summary,
            opportunity.buy_venue, opportunity.sell_venue,
        )
        opportunity.opportunity_id = key
        now = time.time()
        previous = self.seen.get(key, 0)
        if previous and now - previous < self.cooldown_seconds:
            self.stats["deduplicated"] += 1
            self._audit("deduplicated", opportunity, "cooldown")
            return None
        self.seen[key] = now
        self.opportunities[key] = opportunity
        self._audit("discovered", opportunity)
        return opportunity

    def validate(
        self,
        opportunity: Opportunity,
        *,
        min_confidence: float = 0.70,
        min_liquidity: float = 0.20,
        min_net_edge: float = 0.005,
    ) -> Opportunity:
        reasons = []
        if not 0 <= opportunity.confidence <= 1:
            reasons.append("invalid confidence")
        if not 0 <= opportunity.risk <= 1:
            reasons.append("invalid risk")
        if opportunity.category == "arbitrage" and opportunity.net_edge < min_net_edge:
            reasons.append(f"net edge below threshold: {opportunity.net_edge:.4%}")
        if opportunity.confidence < min_confidence:
            reasons.append("confidence below threshold")
        if opportunity.liquidity < min_liquidity:
            reasons.append("liquidity below threshold")
        if not opportunity.sources:
            reasons.append("no sources")
        if not opportunity.summary.strip():
            reasons.append("empty summary")

        opportunity.validated_at = time.time()
        if reasons:
            opportunity.status = "rejected"
            opportunity.rejection_reason = "; ".join(reasons)
            self.stats["rejected"] += 1
            self._audit("rejected", opportunity, opportunity.rejection_reason)
            return opportunity

        opportunity.score = self.score(opportunity)
        opportunity.status = "validated"
        self.stats["validated"] += 1
        self._audit("validated", opportunity)
        return opportunity

    @staticmethod
    def score(o: Opportunity) -> float:
        edge = max(0.0, min(1.0, o.net_edge / 0.02))
        return round(
            0.40 * o.confidence
            + 0.25 * o.liquidity
            + 0.20 * edge
            + 0.15 * (1.0 - o.risk),
            6,
        )

    def consensus(self, opportunity: Opportunity, validators: Iterable[str], required: int = 2) -> bool:
        ids = list(dict.fromkeys([*opportunity.agents, *validators]))
        opportunity.agents = ids
        ok = len(ids) >= max(1, required)
        self._audit("consensus", opportunity, f"validators={len(ids)} required={required} result={ok}")
        return ok

    def should_alert(
        self,
        opportunity: Opportunity,
        *,
        critical_score: float = 0.88,
        high_score: float = 0.70,
    ) -> str | None:
        if opportunity.status != "validated":
            return None
        if opportunity.category == "arbitrage" and opportunity.net_edge < 0.005:
            return None
        if opportunity.score >= critical_score:
            self.stats["alerts"] += 1
            return "CRITICAL"
        if opportunity.score >= high_score:
            self.stats["alerts"] += 1
            return "HIGH"
        return None

    def _audit(self, event: str, opportunity: Opportunity, reason: str = "") -> None:
        record = {
            "timestamp": time.time(),
            "event": event,
            "reason": reason,
            "opportunity": asdict(opportunity),
            "net_edge": opportunity.net_edge,
        }
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")

    def snapshot(self) -> dict:
        return {
            "stats": dict(self.stats),
            "opportunities": len(self.opportunities),
            "audit_path": str(self.audit_path),
        }
