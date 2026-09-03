from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenRisk:
    symbol: str
    address: str
    chain: str
    liquidity_usd: float
    suspicious: bool
    reasons: tuple[str, ...]


def assess_token(symbol: str, address: str, chain: str, liquidity_usd: float, volume_24h_usd: float = 0.0) -> TokenRisk:
    reasons: list[str] = []
    if not address or len(address) < 10:
        reasons.append("missing or malformed token address")
    if liquidity_usd < 10_000:
        reasons.append("very low liquidity")
    if volume_24h_usd and volume_24h_usd > liquidity_usd * 50:
        reasons.append("extreme volume-to-liquidity ratio")
    return TokenRisk(symbol, address, chain, liquidity_usd, bool(reasons), tuple(reasons))
