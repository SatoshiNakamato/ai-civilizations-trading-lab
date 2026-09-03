from __future__ import annotations

from dataclasses import dataclass

from .cross_exchange import CrossExchangeArbitrageLab, CrossExchangeOpportunity
from .dex_data import DEXQuote, PublicDEXData


@dataclass(frozen=True)
class ResearchOpportunity:
    symbol: str
    buy_venue: str
    sell_venue: str
    buy_price: float
    sell_price: float
    gross_spread_pct: float
    liquidity_usd: float
    source: str
    executable_candidate: bool
    reason: str


class OpportunityEngine:
    """Unified read-only scanner for CEX and DEX price discrepancies."""

    def __init__(self, cex: CrossExchangeArbitrageLab | None = None, dex: PublicDEXData | None = None):
        self.cex = cex or CrossExchangeArbitrageLab()
        self.dex = dex or PublicDEXData()

    def scan(self, symbols: list[str] | None = None) -> dict:
        symbols = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        cex_results = self.cex.inspect(symbols)
        dex_queries = ["WETH USDC", "WBTC USDC", "SOL USDC"]
        dex_results: list[DEXQuote] = self.dex.snapshot(dex_queries)
        return {
            "cex": cex_results,
            "dex": dex_results,
            "summary": {
                "cex_candidates": len(cex_results),
                "dex_quotes": len(dex_results),
                "positive_cex_net": sum(1 for x in cex_results if x.executable),
            },
        }
