from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
from typing import Iterable


@dataclass(frozen=True)
class PaperFill:
    trade_id: str
    opportunity_id: str
    agent: str
    side: str
    symbol: str
    quantity: float
    requested_price: float
    fill_price: float
    fees: float = 0.0
    slippage: float = 0.0
    timestamp: float = 0.0

    @property
    def gross_value(self) -> float:
        return self.quantity * self.fill_price

    @property
    def total_cost(self) -> float:
        return abs(self.quantity * self.requested_price) * self.slippage + self.fees


class PaperTradingLedger:
    """Append-only, deterministic paper fills with duplicate protection."""

    def __init__(self, path: str = "data/paper_trades.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ids = self._load_ids()

    def _load_ids(self) -> set[str]:
        if not self.path.exists():
            return set()
        ids: set[str] = set()
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                if row.get("trade_id"):
                    ids.add(str(row["trade_id"]))
            except json.JSONDecodeError:
                continue
        return ids

    def record(self, fill: PaperFill) -> PaperFill:
        if fill.trade_id in self._ids:
            raise ValueError(f"duplicate paper trade: {fill.trade_id}")
        if fill.quantity <= 0 or fill.requested_price <= 0 or fill.fill_price <= 0:
            raise ValueError("quantity and prices must be positive")
        if fill.fees < 0 or fill.slippage < 0:
            raise ValueError("fees and slippage cannot be negative")
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(fill), separators=(",", ":")) + "\n")
        self._ids.add(fill.trade_id)
        return fill

    def read(self) -> list[PaperFill]:
        rows: list[PaperFill] = []
        if not self.path.exists():
            return rows
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(PaperFill(**json.loads(line)))
            except (json.JSONDecodeError, TypeError):
                continue
        return rows

    def validate(self, fills: Iterable[PaperFill] | None = None) -> dict:
        values = list(self.read() if fills is None else fills)
        ids = [x.trade_id for x in values]
        return {
            "trades": len(values),
            "unique_trade_ids": len(set(ids)),
            "duplicate_trade_ids": len(ids) - len(set(ids)),
            "valid": len(ids) == len(set(ids)) and all(
                x.quantity > 0 and x.requested_price > 0 and x.fill_price > 0
                and x.fees >= 0 and x.slippage >= 0 for x in values
            ),
        }
