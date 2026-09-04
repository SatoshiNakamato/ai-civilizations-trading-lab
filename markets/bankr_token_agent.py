from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
import re
import time
import urllib.request
import urllib.error


@dataclass
class TokenPlan:
    agent: str
    name: str
    symbol: str
    chain: str
    thesis: str
    score: float
    status: str = "planned"
    token_address: str = ""
    tx_hash: str = ""
    created_at: float = 0.0


class BankrTokenAgent:
    """Bankr integration with a safe dry-run default.

    Agents can research and score token concepts autonomously. Live deployment is
    opt-in via BANKR_LIVE_DEPLOY=1 and a user API key; no credentials are stored
    in the repository. Partner-key deployments are intentionally not attempted.
    """

    ENDPOINT = "https://api.bankr.bot/token-launches/deploy"

    def __init__(self, audit_path="data/bankr_token_plans.jsonl", live=None):
        self.audit_path = audit_path
        self.live = (os.getenv("BANKR_LIVE_DEPLOY") == "1") if live is None else bool(live)
        os.makedirs(os.path.dirname(audit_path) or ".", exist_ok=True)

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        value = re.sub(r"[^A-Za-z0-9]", "", symbol).upper()
        return value[:10] or "AGENT"

    def plan(self, agent, name, symbol, thesis, score, chain="base"):
        chain = chain.lower()
        if chain not in {"base", "robinhood"}:
            raise ValueError("Bankr token launch chain must be base or robinhood")
        plan = TokenPlan(agent, name[:100], self.normalize_symbol(symbol), chain,
                         thesis[:500], float(score), created_at=time.time())
        self._audit(plan)
        return plan

    def simulate(self, plan: TokenPlan):
        result = TokenPlan(**asdict(plan))
        result.status = "simulated"
        self._audit(result)
        return result

    def deploy(self, plan: TokenPlan):
        if not self.live:
            return self.simulate(plan)
        key = os.getenv("BANKR_API_KEY")
        if not key:
            raise RuntimeError("BANKR_API_KEY is required for live deployment")
        payload = json.dumps({
            "tokenName": plan.name,
            "tokenSymbol": plan.symbol,
            "description": plan.thesis,
            "chain": plan.chain,
            "quoteOnlyFees": True,
            "simulateOnly": False,
        }).encode()
        request = urllib.request.Request(
            self.ENDPOINT, data=payload,
            headers={"Content-Type": "application/json", "X-API-Key": key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Bankr deployment failed: HTTP {exc.code}") from exc
        result = TokenPlan(**asdict(plan))
        result.status = "deployed"
        result.token_address = str(body.get("tokenAddress", body.get("token_address", "")))
        result.tx_hash = str(body.get("txHash", body.get("tx_hash", "")))
        self._audit(result)
        return result

    def _audit(self, plan):
        with open(self.audit_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(plan), sort_keys=True) + "\n")

    def snapshot(self):
        return {"live": self.live, "audit_path": self.audit_path}
