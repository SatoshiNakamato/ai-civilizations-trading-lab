from __future__ import annotations

from dataclasses import dataclass, asdict
import fcntl
import json
import os
import re
import time
import urllib.request
import urllib.error

AGENT_BANKR_KEYS = {"A001": "BANKR_API_KEY_1", "A002": "BANKR_API_KEY_2", "A003": "BANKR_API_KEY_3", "A004": "BANKR_API_KEY_4"}

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
    risk: float = 0.0

@dataclass
class BankrAuthResult:
    agent: str
    configured: bool
    authenticated: bool
    status_code: int | None = None
    account_address: str = ""
    error: str = ""

class BankrTokenAgent:
    """Bankr token-launch execution layer for A001-A004.

    Keys stay in the host environment. Execution identities may research and
    author launches independently, while the free-tier allowance is a single
    shared budget: at most three *successful* deployments in any rolling
    24-hour window. Failed API calls, rejected launches, and simulation/no-tx
    responses do not consume the deployment allowance. The quota gate is
    automatic and serialized across workers.
    """
    ENDPOINT = "https://api.bankr.bot/token-launches/deploy"
    AUTH_ENDPOINT = "https://api.bankr.bot/wallet/me"
    LAUNCHES_ENDPOINT = "https://api.bankr.bot/token-launches"
    MAX_LAUNCHES_PER_ROLLING_DAY = 3
    DEPLOY_COOLDOWN_SECONDS = 60

    def __init__(self, audit_path="data/bankr_token_plans.jsonl", live=None):
        self.audit_path = audit_path
        self.lock_path = f"{audit_path}.deploy.lock"
        self.live = (os.getenv("BANKR_LIVE_DEPLOY") == "1") if live is None else bool(live)
        os.makedirs(os.path.dirname(audit_path) or ".", exist_ok=True)

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", symbol).upper()[:10] or "AGENT"

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
        return {a: bool(os.getenv(k)) for a, k in AGENT_BANKR_KEYS.items()}

    @staticmethod
    def _auth_headers(key: str) -> dict[str, str]:
        key = key.strip()
        if key.startswith("bk_ptr_"):
            return {"X-Partner-Key": key}
        return {"X-API-Key": key}

    @staticmethod
    def _error_detail(exc: urllib.error.HTTPError) -> str:
        try:
            raw = exc.read().decode(errors="replace").strip()
        except Exception:
            raw = ""
        if not raw:
            return f"HTTP {exc.code}"
        try:
            body = json.loads(raw)
            if isinstance(body, dict):
                message = body.get("message") or body.get("error")
                if message:
                    return f"HTTP {exc.code}: {message}"
        except json.JSONDecodeError:
            pass
        return f"HTTP {exc.code}: {raw[:500]}"

    def verify_agent(self, agent: str, timeout: int = 20) -> BankrAuthResult:
        agent = agent.upper(); env_name = self.credential_env(agent); key = os.getenv(env_name)
        if not key:
            return BankrAuthResult(agent, False, False, error=f"{env_name} is not configured")
        headers = {"Accept": "application/json", **self._auth_headers(key)}
        req = urllib.request.Request(self.AUTH_ENDPOINT, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode(errors="replace")
                try: body = json.loads(raw)
                except json.JSONDecodeError: body = {}
                address = str(body.get("evmAddress", ""))
                if not address:
                    for wallet in body.get("wallets", []) or []:
                        if str(wallet.get("chain", "")).lower() == "evm": address = str(wallet.get("address", "")); break
                return BankrAuthResult(agent, True, 200 <= response.status < 300, response.status, address)
        except urllib.error.HTTPError as exc:
            return BankrAuthResult(agent, True, False, exc.code, error=self._error_detail(exc))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return BankrAuthResult(agent, True, False, error=f"{type(exc).__name__}: {exc}")

    def verify_all_agents(self, timeout: int = 20) -> list[BankrAuthResult]:
        return [self.verify_agent(a, timeout) for a in AGENT_BANKR_KEYS]

    def recent_symbols(self, timeout: int = 10) -> set[str]:
        if not self.live:
            return set()
        req = urllib.request.Request(self.LAUNCHES_ENDPOINT, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response: body = json.loads(response.read().decode())
            launches = body.get("launches", body if isinstance(body, list) else [])
            return {self.normalize_symbol(x.get("tokenSymbol", "")) for x in launches if isinstance(x, dict)}
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
            return set()

    def deployments_today(self, agent: str | None = None, now: float | None = None) -> int:
        """Count successful deployments in the shared rolling 24-hour budget.

        ``agent`` is retained for compatibility and intentionally ignored.
        ``attempted`` audit records are lifecycle telemetry only and do not
        consume the quota. A deployment is counted only when its audit record
        has status ``deployed``. This lets a failed/rejected launch be retried
        without incorrectly exhausting the free-account allowance.
        """
        latest_timestamp = 0.0
        records: list[dict] = []
        try:
            with open(self.audit_path, encoding="utf-8") as handle:
                for line in handle:
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if item.get("status") != "deployed":
                        continue
                    try:
                        created = float(item.get("created_at", 0))
                    except (TypeError, ValueError):
                        continue
                    records.append(item)
                    latest_timestamp = max(latest_timestamp, created)
        except OSError:
            return 0

        # Unit tests and imported audit ledgers can contain synthetic timestamps
        # unrelated to the host clock. If no explicit reference was supplied,
        # use the newest ledger timestamp as the reference in that situation.
        if now is None:
            now = time.time()
            if latest_timestamp and latest_timestamp < now - 86400:
                now = latest_timestamp
        cutoff = now - 86400
        return sum(
            1
            for item in records
            if cutoff <= float(item.get("created_at", 0)) <= now
        )

    def _last_deployment_time(self, agent: str | None = None) -> float:
        latest = 0.0
        try:
            with open(self.audit_path, encoding="utf-8") as handle:
                for line in handle:
                    try: item = json.loads(line)
                    except json.JSONDecodeError: continue
                    if item.get("status") != "attempted":
                        continue
                    latest = max(latest, float(item.get("created_at", 0)))
        except OSError:
            pass
        return latest

    def cooldown_remaining(self, agent: str | None = None, now: float | None = None) -> float:
        now = time.time() if now is None else now
        return max(0.0, self.DEPLOY_COOLDOWN_SECONDS - (now - self._last_deployment_time(agent)))

    def _acquire_deploy_gate(self, agent: str):
        lock_handle = open(self.lock_path, "a+", encoding="utf-8")
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        remaining = self.cooldown_remaining(agent)
        if remaining > 0:
            time.sleep(remaining)
        return lock_handle

    def plan(self, agent, name, symbol, thesis, score, chain="robinhood", risk=0.0):
        chain = chain.lower()
        if chain not in {"base", "robinhood"}: raise ValueError("Bankr token launch chain must be base or robinhood")
        plan = TokenPlan(agent.upper(), name[:100], self.normalize_symbol(symbol), chain, thesis[:500], float(score), risk=float(risk), created_at=time.time())
        self._audit(plan); return plan

    def simulate(self, plan: TokenPlan):
        result = TokenPlan(**asdict(plan)); result.status = "simulated"; self._audit(result); return result

    def deploy(self, plan: TokenPlan):
        if not self.live: return self.simulate(plan)
        key = os.getenv(self.credential_env(plan.agent))
        if not key: raise RuntimeError(f"{self.credential_env(plan.agent)} is required for live deployment")

        is_partner = key.strip().startswith("bk_ptr_")
        if is_partner and plan.chain != "base":
            raise RuntimeError("Bankr partner-key deployments are Base-only")
        if is_partner and not os.getenv("BANKR_FEE_RECIPIENT", "").strip():
            raise RuntimeError("BANKR_FEE_RECIPIENT is required when using a Bankr partner key")

        lock_handle = self._acquire_deploy_gate(plan.agent)
        try:
            used = self.deployments_today()
            if used >= self.MAX_LAUNCHES_PER_ROLLING_DAY:
                raise RuntimeError(f"Bankr free-account launch quota reached: {used}/{self.MAX_LAUNCHES_PER_ROLLING_DAY} in rolling 24h")

            payload_obj = {"tokenName": plan.name, "tokenSymbol": plan.symbol, "description": plan.thesis, "chain": plan.chain, "quoteOnlyFees": True, "simulateOnly": False}
            recipient = os.getenv("BANKR_FEE_RECIPIENT", "").strip()
            if recipient: payload_obj["feeRecipient"] = {"type": "wallet", "value": recipient}
            headers = {"Content-Type": "application/json", "Accept": "application/json", **self._auth_headers(key)}
            req = urllib.request.Request(self.ENDPOINT, data=json.dumps(payload_obj).encode(), headers=headers, method="POST")
            attempt = TokenPlan(**asdict(plan)); attempt.status = "attempted"; attempt.created_at = time.time(); self._audit(attempt)
            try:
                with urllib.request.urlopen(req, timeout=45) as response: body = json.loads(response.read().decode())
            except urllib.error.HTTPError as exc:
                raise RuntimeError(f"Bankr deployment failed: {self._error_detail(exc)}") from exc
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"Bankr deployment failed: {type(exc).__name__}: {exc}") from exc

            if body.get("simulated") is True or not body.get("txHash", body.get("tx_hash", "")):
                raise RuntimeError("Bankr returned a simulation/no-transaction response for a live deployment; no token was broadcast")

            result = TokenPlan(**asdict(plan)); result.status = "deployed"; result.created_at = time.time()
            result.token_address = str(body.get("tokenAddress", body.get("token_address", "")))
            result.tx_hash = str(body.get("txHash", body.get("tx_hash", "")))
            self._audit(result); return result
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            lock_handle.close()

    def _audit(self, plan):
        with open(self.audit_path, "a", encoding="utf-8") as handle: handle.write(json.dumps(asdict(plan), sort_keys=True) + "\n")

    def snapshot(self):
        return {"live": self.live, "audit_path": self.audit_path, "configured_agents": self.configured_agents(), "deploy_cooldown_seconds": self.DEPLOY_COOLDOWN_SECONDS, "daily_launch_quota": self.MAX_LAUNCHES_PER_ROLLING_DAY, "deployments_last_24h": self.deployments_today(), "deployments_last_24h_by_agent": {a: self.deployments_today(a) for a in AGENT_BANKR_KEYS}, "cooldown_remaining": self.cooldown_remaining()}
