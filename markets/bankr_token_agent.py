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


@dataclass
class BankrAuthResult:
    agent: str
    configured: bool
    authenticated: bool
    status_code: int | None = None
    account_address: str = ""
    error: str = ""


class BankrTokenAgent:
    """Bankr token-launch execution layer.

    A001-A004 are the only agents allowed to use the four configured keys.
    The application never stores keys in Git. For production, each Bankr key
    should have token-launch enabled while wallet write access remains disabled.

    Live deployment is opt-in through BANKR_LIVE_DEPLOY=1. The hosted worker
    can therefore run continuously without broadcasting until the operator
    explicitly enables live launch execution.
    """

    ENDPOINT = "https://api.bankr.bot/token-launches/deploy"
    AUTH_ENDPOINT = "https://api.bankr.bot/wallet/me"
    LAUNCHES_ENDPOINT = "https://api.bankr.bot/token-launches"

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

    def verify_agent(self, agent: str, timeout: int = 20) -> BankrAuthResult:
        agent = agent.upper()
        env_name = self.credential_env(agent)
        key = os.getenv(env_name)
        if not key:
            return BankrAuthResult(agent, False, False, error=f"{env_name} is not configured")
        request = urllib.request.Request(
            self.AUTH_ENDPOINT,
            headers={"Accept": "application/json", "X-API-Key": key},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode(errors="replace")
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError:
                    body = {}
                address = str(body.get("evmAddress", ""))
                if not address:
                    for wallet in body.get("wallets", []) or []:
                        if str(wallet.get("chain", "")).lower() == "evm":
                            address = str(wallet.get("address", ""))
                            break
                return BankrAuthResult(agent, True, 200 <= response.status < 300,
                                       status_code=response.status, account_address=address)
        except urllib.error.HTTPError as exc:
            return BankrAuthResult(agent, True, False, status_code=exc.code, error=f"HTTP {exc.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return BankrAuthResult(agent, True, False, error=f"{type(exc).__name__}: {exc}")

    def verify_all_agents(self, timeout: int = 20) -> list[BankrAuthResult]:
        return [self.verify_agent(agent, timeout=timeout) for agent in AGENT_BANKR_KEYS]

    def recent_symbols(self, timeout: int = 10) -> set[str]:
        """Fetch public Bankr launches so the ticker brain can avoid collisions."""
        request = urllib.request.Request(self.LAUNCHES_ENDPOINT, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode())
            launches = body.get("launches", body if isinstance(body, list) else [])
            return {self.normalize_symbol(x.get("tokenSymbol", "")) for x in launches if isinstance(x, dict)}
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
            return set()

    def plan(self, agent, name, symbol, thesis, score, chain="robinhood"):
        chain = chain.lower()
        if chain not in {"base", "robinhood"}:
            raise ValueError("Bankr token launch chain must be base or robinhood")
        plan = TokenPlan(agent.upper(), name[:100], self.normalize_symbol(symbol), chain,
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

        payload_obj = {
            "tokenName": plan.name,
            "tokenSymbol": plan.symbol,
            "description": plan.thesis,
            "chain": plan.chain,
            "quoteOnlyFees": True,
            "simulateOnly": False,
        }
        fee_recipient = os.getenv("BANKR_FEE_RECIPIENT", "").strip()
        if fee_recipient:
            payload_obj["feeRecipient"] = {"type": "wallet", "value": fee_recipient}

        payload = json.dumps(payload_obj).encode()
        request = urllib.request.Request(
            self.ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json", "X-API-Key": key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Bankr deployment failed: HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Bankr deployment failed: {type(exc).__name__}: {exc}") from exc

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
        return {
            "live": self.live,
            "audit_path": self.audit_path,
            "configured_agents": self.configured_agents(),
        }
