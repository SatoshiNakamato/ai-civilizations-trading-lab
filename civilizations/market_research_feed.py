from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class MarketObservation:
    asset: str
    price_usd: float
    change_24h: float
    source: str = "coingecko"


class PublicMarketResearchFeed:
    """Small, keyless public market feed with graceful degradation.

    The feed is advisory only. It never holds credentials and never executes
    trades. A failed public request simply returns an empty observation set.
    """

    IDS = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "DOGE": "dogecoin",
        "PEPE": "pepe",
    }
    ENDPOINT = "https://api.coingecko.com/api/v3/simple/price"

    def fetch(self, timeout: int = 8) -> list[MarketObservation]:
        ids = ",".join(self.IDS.values())
        url = f"{self.ENDPOINT}?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "ai-civilizations-trading-lab/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = json.loads(response.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
            return []
        reverse = {v: k for k, v in self.IDS.items()}
        result: list[MarketObservation] = []
        for coin_id, asset in reverse.items():
            item = body.get(coin_id, {})
            try:
                result.append(MarketObservation(asset, float(item["usd"]), float(item.get("usd_24h_change", 0.0) or 0.0)))
            except (KeyError, TypeError, ValueError):
                continue
        return result
