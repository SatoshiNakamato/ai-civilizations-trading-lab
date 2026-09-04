from __future__ import annotations

from dataclasses import dataclass, asdict
import time


@dataclass
class TradeIntent:
    agent: str
    symbol: str
    side: str
    amount: float
    reference_price: float
    confidence: float
    thesis: str
    signal_id: str


class LiveTradingRuntime:
    """Connects civilization decisions to the guarded live execution boundary."""

    def __init__(self, engine, min_confidence=0.70):
        self.engine = engine
        self.min_confidence = min_confidence
        self.executed = 0
        self.rejected = 0

    def execute(self, intent: TradeIntent):
        if intent.confidence < self.min_confidence:
            self.rejected += 1
            return {"status": "rejected", "reason": "confidence below live threshold", "intent": asdict(intent)}
        if intent.side not in {"buy", "sell"}:
            self.rejected += 1
            return {"status": "rejected", "reason": "invalid side", "intent": asdict(intent)}
        result = self.engine.market_order(
            symbol=intent.symbol,
            side=intent.side,
            amount=intent.amount,
            estimated_price=intent.reference_price,
            client_ref=intent.signal_id,
        )
        self.executed += 1
        return {"status": result["status"], "intent": asdict(intent), "execution": result, "created_at": time.time()}

    def snapshot(self):
        return {"executed": self.executed, "rejected": self.rejected, "engine": self.engine.snapshot()}
