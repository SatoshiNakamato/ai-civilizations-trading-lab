from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class DEXQuote:
    venue: str
    chain: str
    symbol: str
    price: float
    liquidity_usd: float
    url: str
    timestamp: float


class PublicDEXData:
    """Read-only DEX discovery using public market-data endpoints.

    This layer deliberately does not submit swaps or interact with wallets.
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def _get_json(self, url: str):
        req = urllib.request.Request(url, headers={"User-Agent": "ai-civilizations-trading-lab/1.0"})
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode())

    def search_pairs(self, query: str, limit: int = 20) -> list[DEXQuote]:
        url = "https://api.dexscreener.com/latest/dex/search/?" + urllib.parse.urlencode({"q": query})
        data = self._get_json(url)
        result: list[DEXQuote] = []
        for pair in data.get("pairs", [])[:limit]:
            try:
                price = float(pair.get("priceUsd") or 0)
                liquidity = float((pair.get("liquidity") or {}).get("usd") or 0)
                if price <= 0:
                    continue
                result.append(DEXQuote(
                    venue=str(pair.get("dexId") or "unknown").upper(),
                    chain=str(pair.get("chainId") or "unknown"),
                    symbol=f"{pair.get('baseToken', {}).get('symbol', '?')}/{pair.get('quoteToken', {}).get('symbol', '?')}",
                    price=price,
                    liquidity_usd=liquidity,
                    url=str(pair.get("url") or ""),
                    timestamp=time.time(),
                ))
            except (TypeError, ValueError):
                continue
        return result

    def snapshot(self, queries: list[str] | None = None, limit: int = 20) -> list[DEXQuote]:
        quotes: list[DEXQuote] = []
        for query in queries or ["WETH USDC", "WBTC USDC", "SOL USDC"]:
            try:
                quotes.extend(self.search_pairs(query, limit))
            except Exception:
                continue
        return quotes
