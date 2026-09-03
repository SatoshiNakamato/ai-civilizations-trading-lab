from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionEstimate:
    venue: str
    side: str
    requested_usd: float
    executable_usd: float
    average_price: float
    price_impact_pct: float
    fee_usd: float
    gas_usd: float
    net_usd: float
    executable: bool
    reason: str


def estimate_amm_trade(price: float, liquidity_usd: float, requested_usd: float, side: str, fee_pct: float = 0.30, gas_usd: float = 0.0) -> ExecutionEstimate:
    if price <= 0 or liquidity_usd <= 0 or requested_usd <= 0:
        return ExecutionEstimate("DEX", side, requested_usd, 0.0, price, 0.0, 0.0, gas_usd, -gas_usd, False, "invalid market data")
    # Constant-product approximation: x*y=k. For a pool whose USD liquidity is
    # approximately 2*x*price, reserve in USD is liquidity/2. This is a
    # research approximation, not an execution guarantee.
    reserve = liquidity_usd / 2.0
    impact = requested_usd / max(reserve, 1e-12)
    if side == "buy":
        avg = price * (1.0 + impact / 2.0)
    else:
        avg = price * max(1.0 - impact / 2.0, 0.000001)
    executable_usd = min(requested_usd, max(liquidity_usd * 0.01, 0.0))
    fee = executable_usd * fee_pct / 100.0
    net = -fee - gas_usd
    ok = executable_usd >= requested_usd and impact * 100 < 5.0
    reason = "within modeled depth" if ok else "insufficient modeled depth or excessive price impact"
    return ExecutionEstimate("DEX", side, requested_usd, executable_usd, avg, impact * 100, fee, gas_usd, net, ok, reason)


def round_trip_profit(buy_price: float, sell_price: float, size_usd: float, buy_cost_pct: float, sell_cost_pct: float) -> float:
    if buy_price <= 0 or sell_price <= 0 or size_usd <= 0:
        return 0.0
    gross = size_usd * (sell_price / buy_price - 1.0)
    costs = size_usd * (buy_cost_pct + sell_cost_pct) / 100.0
    return gross - costs
