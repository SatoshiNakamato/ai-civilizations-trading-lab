from __future__ import annotations

from dataclasses import dataclass
from .real_data import PublicMarketData


@dataclass
class ArbitrageFinding:
    symbol: str
    bid: float
    ask: float
    spread_pct: float
    source: str
    executable: bool = False


class ArbitrageResearchLab:
    """Research-only single-venue quote spread monitor.

    It deliberately does not place orders or move funds. Cross-venue execution
    requires independently collected quotes, fees, latency and liquidity checks.
    """
    def __init__(self, provider: PublicMarketData | None = None):
        self.provider = provider or PublicMarketData()

    def inspect(self, symbols: list[str] | None = None) -> list[ArbitrageFinding]:
        symbols = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        out = []
        for symbol in symbols:
            snap = self.provider.snapshot(symbol, "1m", 20)
            bid = float(snap["ticker"]["bidPrice"])
            ask = float(snap["ticker"]["askPrice"])
            mid = (bid + ask) / 2 if bid and ask else 0.0
            spread = ((ask - bid) / mid * 100) if mid else 0.0
            out.append(ArbitrageFinding(symbol, bid, ask, spread, snap["source"]))
        return out
