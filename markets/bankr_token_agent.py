from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
import re
import time
import urllib.request
import urllib.error


AGENT_BANKR_KEYS = {
    "A001": "BANKR_API_KEY_1",
    "A002": "BANKR_API_KEY_2",
    "A003": "BANKR_API_KEY_3",
    "A004": "BANKR_API_KEY_4",
}


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

    Each execution agent maps to its own local Bankr API-key environment variable.
    Credentials are never stored in the repository or exposed to research agents.
    Live deployment remains opt-in via BANKR_LIVE_DEPLOY=1.
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

    @staticmethod
    def credential_env(agent: str) -> str:
        agent = agent.upper()
        if agent in AGENT_BANKR_KEYS:
            return AGENT_BANKR_KEYS[agent]
        raise ValueError("No Bankr credential is assigned to this agent")

    @classmethod
    def credential_configured(cls, agent: str) -> bool:
        return bool(os.getenv(cls.credential_env(agent)))

    @classmethod
    def configured_agents(cls) -> dict[str, bool]:
        return {agent: bool(os.getenv(env_name)) for agent, env_name in AGENT_BANKR_KEYS.items()}

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
        env_name = self.credential_env(plan.agent)
        key = os.getenv(env_name)
        if not key:
            raise RuntimeError(f"{env_name} is required for live deployment")
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
        return {"live": self.live, "audit_path": self.audit_path,
                "configured_agents": self.configured_agents()}
