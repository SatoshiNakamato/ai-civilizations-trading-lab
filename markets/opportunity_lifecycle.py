from __future__ import annotations

from dataclasses import dataclass, asdict
from time import time


@dataclass(frozen=True)
class DepthLevel:
    price: float
    quantity: float


@dataclass(frozen=True)
class DepthExecution:
    side: str
    requested_usd: float
    filled_usd: float
    average_price: float
    fee_usd: float
    slippage_pct: float
    complete: bool


@dataclass(frozen=True)
class OpportunityAssessment:
    symbol: str
    buy_venue: str
    sell_venue: str
    size_usd: float
    gross_usd: float
    fees_usd: float
    gas_usd: float
    slippage_usd: float
    latency_haircut_usd: float
    expected_net_usd: float
    confidence: float
    executable: bool
    reason: str
    timestamp: float


def execute_against_depth(side: str, levels: list[DepthLevel], requested_usd: float, fee_pct: float = 0.0) -> DepthExecution:
    remaining = requested_usd
    notional = 0.0
    units = 0.0
    for level in levels:
        if level.price <= 0 or level.quantity <= 0:
            continue
        available_usd = level.price * level.quantity
        take_usd = min(remaining, available_usd)
        notional += take_usd
        units += take_usd / level.price
        remaining -= take_usd
        if remaining <= 1e-9:
            break
    complete = remaining <= 1e-9 and units > 0
    avg = notional / units if units else 0.0
    fee = notional * fee_pct / 100.0
    slippage = 0.0
    if levels and avg and levels[0].price:
        slippage = abs(avg / levels[0].price - 1.0) * 100.0
    return DepthExecution(side, requested_usd, notional, avg, fee, slippage, complete)


class OpportunityMemory:
    """Small in-process memory of opportunity outcomes for research feedback."""
    def __init__(self):
        self.records: list[dict] = []

    def record(self, assessment: OpportunityAssessment, outcome: str, realized_net_usd: float | None = None):
        self.records.append({**asdict(assessment), "outcome": outcome, "realized_net_usd": realized_net_usd, "recorded_at": time()})

    def statistics(self) -> dict:
        total = len(self.records)
        wins = sum(r["outcome"] == "success" for r in self.records)
        failures = sum(r["outcome"] == "failure" for r in self.records)
        return {"records": total, "successes": wins, "failures": failures, "success_rate": wins / total if total else 0.0}


def assess_opportunity(symbol: str, buy_ask: float, sell_bid: float, size_usd: float, buy_fee_pct: float, sell_fee_pct: float, gas_usd: float = 0.0, latency_haircut_pct: float = 0.0, buy_depth: list[DepthLevel] | None = None, sell_depth: list[DepthLevel] | None = None) -> OpportunityAssessment:
    buy_depth = buy_depth or [DepthLevel(buy_ask, size_usd / buy_ask if buy_ask > 0 else 0)]
    sell_depth = sell_depth or [DepthLevel(sell_bid, size_usd / sell_bid if sell_bid > 0 else 0)]
    buy = execute_against_depth("buy", buy_depth, size_usd, buy_fee_pct)
    sell = execute_against_depth("sell", sell_depth, size_usd, sell_fee_pct)
    comparable = min(buy.filled_usd, sell.filled_usd)
    gross = comparable * (sell.average_price / buy.average_price - 1.0) if buy.average_price and sell.average_price else 0.0
    fees = buy.fee_usd + sell.fee_usd
    slippage = comparable * (buy.slippage_pct + sell.slippage_pct) / 100.0
    latency = max(gross, 0.0) * latency_haircut_pct / 100.0
    net = gross - fees - gas_usd - slippage - latency
    confidence = 0.0
    if comparable > 0:
        confidence = min(1.0, max(0.0, (comparable / max(size_usd, 1.0)) * (1.0 - min((buy.slippage_pct + sell.slippage_pct) / 10.0, 1.0))))
    executable = buy.complete and sell.complete and net > 0
    reason = "positive modeled net after depth, fees, gas and slippage" if executable else "not profitable or insufficient executable depth"
    return OpportunityAssessment(symbol, "BUY", "SELL", size_usd, gross, fees, gas_usd, slippage, latency, net, confidence, executable, reason, time())
