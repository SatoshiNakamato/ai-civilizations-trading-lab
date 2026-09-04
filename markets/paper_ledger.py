from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PaperTrade:
    trade_id: str
    opportunity_id: str
    asset: str
    buy_venue: str
    sell_venue: str
    quantity: float
    buy_price: float
    sell_price: float
    fees: float
    net_pnl: float
    created_at: float


class PaperLedger:
    """Audit-only ledger for hypothetical opportunities; never submits orders."""

    def __init__(self, path: str = "data/paper_trades.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.trades: list[PaperTrade] = []

    def record(self, opportunity, quantity: float = 0.01) -> PaperTrade:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if opportunity.buy_price <= 0 or opportunity.sell_price <= 0:
            raise ValueError("prices must be positive")
        gross = (opportunity.sell_price - opportunity.buy_price) * quantity
        fees = opportunity.fees * opportunity.buy_price * quantity
        trade = PaperTrade(
            trade_id=f"paper-{len(self.trades)+1:08d}",
            opportunity_id=opportunity.opportunity_id,
            asset=opportunity.asset,
            buy_venue=opportunity.buy_venue,
            sell_venue=opportunity.sell_venue,
            quantity=quantity,
            buy_price=opportunity.buy_price,
            sell_price=opportunity.sell_price,
            fees=fees,
            net_pnl=gross - fees - opportunity.slippage * opportunity.buy_price * quantity,
            created_at=time.time(),
        )
        self.trades.append(trade)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(trade), separators=(",", ":")) + "\n")
        return trade

    def snapshot(self) -> dict:
        return {
            "trades": len(self.trades),
            "net_pnl": round(sum(t.net_pnl for t in self.trades), 8),
            "notional": round(sum(t.quantity * t.buy_price for t in self.trades), 8),
            "path": str(self.path),
            "mode": "paper-only",
        }
