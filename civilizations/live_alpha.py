from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass

from civilizations.email_alerts import AlertCandidate, EmailAlertGateway


@dataclass(frozen=True)
class AlphaToken:
    chain: str
    address: str
    symbol: str
    name: str
    pair_address: str
    url: str
    price_usd: float
    liquidity_usd: float
    volume_24h_usd: float
    price_change_1h: float
    price_change_24h: float
    txns_24h: int
    buys_24h: int
    sells_24h: int
    age_hours: float
    score: float


class LiveAlphaScanner:
    """Keyless public DEX alpha scanner.

    It only reads public market metadata and sends human-readable alerts. It
    never trades, deploys tokens, holds exchange credentials, or submits orders.
    """

    PROFILES = "https://api.dexscreener.com/token-profiles/latest/v1"
    TOKENS = "https://api.dexscreener.com/latest/dex/tokens/{address}"
    DEFAULT_CHAINS = ("base", "solana", "ethereum")

    def __init__(self, gateway: EmailAlertGateway | None = None, timeout: float = 8.0):
        self.gateway = gateway or EmailAlertGateway()
        self.timeout = timeout
        self.seen: dict[str, float] = {}
        self.last_scan: list[AlphaToken] = []
        self.scans = 0
        self.alerts = 0
        self.errors = 0

    def _get(self, url: str):
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "ai-civilizations-trading-lab/1.0"})
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _chain(profile: dict) -> str:
        return str(profile.get("chainId") or profile.get("chain") or "").lower()

    @staticmethod
    def _pair_score(pair: dict, age_hours: float) -> AlphaToken | None:
        base = pair.get("baseToken") or {}
        address = str(base.get("address") or "")
        symbol = str(base.get("symbol") or "").strip()
        name = str(base.get("name") or symbol).strip()
        if not address or not symbol:
            return None
        liquidity = float((pair.get("liquidity") or {}).get("usd") or 0.0)
        volume = float((pair.get("volume") or {}).get("h24") or 0.0)
        change = pair.get("priceChange") or {}
        ch1 = float(change.get("h1") or 0.0)
        ch24 = float(change.get("h24") or 0.0)
        tx = pair.get("txns") or {}
        t24 = tx.get("h24") or {}
        buys = int(t24.get("buys") or 0)
        sells = int(t24.get("sells") or 0)
        total = buys + sells
        if liquidity < 10_000 or volume < 5_000 or total < 20:
            return None
        volume_ratio = min(1.0, volume / max(liquidity, 1.0))
        flow = buys / max(total, 1)
        freshness = max(0.0, 1.0 - age_hours / 48.0)
        momentum = max(0.0, min(1.0, (ch1 + 5.0) / 25.0))
        score = max(0.0, min(1.0, 0.30 * freshness + 0.25 * volume_ratio + 0.20 * flow + 0.15 * momentum + 0.10 * min(1.0, liquidity / 100_000)))
        chain = str(pair.get("chainId") or "").lower()
        pair_address = str(pair.get("pairAddress") or "")
        url = f"https://dexscreener.com/{chain}/{pair_address}" if chain and pair_address else str(pair.get("url") or "")
        price = float(pair.get("priceUsd") or 0.0)
        return AlphaToken(chain, address, symbol, name, pair_address, url, price, liquidity, volume, ch1, ch24, total, buys, sells, age_hours, score)

    def scan(self, *, chains: tuple[str, ...] | None = None, limit: int = 5) -> list[AlphaToken]:
        self.scans += 1
        allowed = set(chains or self.DEFAULT_CHAINS)
        try:
            profiles = self._get(self.PROFILES)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
            self.errors += 1
            self.last_scan = []
            return []
        candidates: list[AlphaToken] = []
        now_ms = time.time() * 1000.0
        for profile in profiles if isinstance(profiles, list) else []:
            chain = self._chain(profile)
            if chain not in allowed:
                continue
            address = str(profile.get("tokenAddress") or profile.get("address") or "")
            if not address:
                continue
            try:
                data = self._get(self.TOKENS.format(address=address))
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
                self.errors += 1
                continue
            for pair in data.get("pairs") or []:
                if str(pair.get("chainId") or "").lower() != chain:
                    continue
                created = float(pair.get("pairCreatedAt") or now_ms)
                age = max(0.0, (now_ms - created) / 3_600_000.0)
                token = self._pair_score(pair, age)
                if token is not None:
                    candidates.append(token)
        candidates.sort(key=lambda x: x.score, reverse=True)
        unique: dict[str, AlphaToken] = {}
        for token in candidates:
            unique.setdefault(f"{token.chain}:{token.address}", token)
        self.last_scan = list(unique.values())[:limit]
        return self.last_scan

    def alert(self, token: AlphaToken, *, agent: str = "ALPHA-SCOUT") -> bool:
        key = f"{token.chain}:{token.address}"
        if time.time() - self.seen.get(key, 0.0) < 86_400:
            return False
        candidate = AlertCandidate(
            title=f"New alpha token: {token.symbol}", category="alpha-token",
            summary=(f"Fresh public DEX pair detected for {token.name} ({token.symbol}). "
                     f"Age={token.age_hours:.1f}h; liquidity=${token.liquidity_usd:,.0f}; "
                     f"24h volume=${token.volume_24h_usd:,.0f}; 1h={token.price_change_1h:+.2f}%; "
                     f"24h={token.price_change_24h:+.2f}%; buys={token.buys_24h}, sells={token.sells_24h}. "
                     "Research alert only; verify liquidity, contract ownership and risk before acting."),
            confidence=min(0.99, 0.70 + token.score * 0.29), edge=max(0.005, min(0.50, token.score * 0.05)),
            risk=0.35, sources=("https://dexscreener.com",), agent=agent,
            token_address=token.address, chain=token.chain, url=token.url,
        )
        sent = self.gateway.send(candidate)
        if sent:
            self.seen[key] = time.time(); self.alerts += 1
        return sent

    def scan_and_alert(self, *, chains: tuple[str, ...] | None = None, limit: int = 5) -> list[AlphaToken]:
        tokens = self.scan(chains=chains, limit=limit)
        for token in tokens:
            if token.score >= 0.70:
                self.alert(token)
        return tokens

    def snapshot(self) -> dict:
        return {"scans": self.scans, "alerts": self.alerts, "errors": self.errors, "last_scan": [asdict(x) for x in self.last_scan], "email": self.gateway.snapshot()}
