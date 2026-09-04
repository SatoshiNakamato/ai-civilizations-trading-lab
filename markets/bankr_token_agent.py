from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
import re
import time
import urllib.request
import urllib.error

# Four Bankr wallets can service the 100-agent population. Agents are mapped
# round-robin to the four host-side credentials; credentials never enter git.
BANKR_KEY_SLOTS = {
    1: "BANKR_API_KEY_1",
    2: "BANKR_API_KEY_2",
    3: "BANKR_API_KEY_3",
    4: "BANKR_API_KEY_4",
}
AGENT_BANKR_KEYS = {f"A{i:03d}": BANKR_KEY_SLOTS[((i - 1) % 4) + 1] for i in range(1, 101)}

NAME_WORDS = (
    "Signal", "Nova", "Pulse", "Vector", "Orbit", "Catalyst", "Beacon", "Axiom",
    "Flux", "Nexus", "Quanta", "Spark", "Vertex", "Prism", "Echo", "Atlas",
)
SYMBOL_WORDS = (
    "SIG", "NOVA", "PULS", "VECT", "ORBT", "CATA", "BNC", "AXM",
    "FLUX", "NEX", "QNT", "SPRK", "VRTX", "PRSM", "ECHO", "ATLS",
)

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
    """Governed Bankr token-launch layer.

    The only state-changing endpoint used is POST /token-launches/deploy.
    Wallet transfer/swap/sign/submit endpoints are deliberately unreachable
    through this class. API keys remain in the host environment.
    """
    ENDPOINT = "https://api.bankr.bot/token-launches/deploy"
    AUTH_ENDPOINT = "https://api.bankr.bot/wallet/me"
    LAUNCHES_ENDPOINT = "https://api.bankr.bot/token-launches"
    MAX_LAUNCHES_PER_WALLET = 3

    def __init__(self, audit_path="data/bankr_token_plans.jsonl", live=None):
        self.audit_path = audit_path
        self.live = (os.getenv("BANKR_LIVE_DEPLOY") == "1") if live is None else bool(live)
        self.auto_deploy = os.getenv("BANKR_AUTO_DEPLOY") == "1"
        os.makedirs(os.path.dirname(audit_path) or ".", exist_ok=True)

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", symbol).upper()[:10] or "AGENT"

    @staticmethod
    def agent_slot(agent: str) -> int:
        match = re.fullmatch(r"A(\d{3})", agent.upper())
        if not match:
            raise ValueError("Agent id must look like A001")
        number = int(match.group(1))
        if not 1 <= number <= 100:
            raise ValueError("Agent id must be between A001 and A100")
        return ((number - 1) % 4) + 1

    @classmethod
    def credential_env(cls, agent: str) -> str:
        return BANKR_KEY_SLOTS[cls.agent_slot(agent)]

    @classmethod
    def credential_configured(cls, agent: str) -> bool:
        return bool(os.getenv(cls.credential_env(agent)))

    @classmethod
    def configured_agents(cls) -> dict[str, bool]:
        configured = {slot: bool(os.getenv(env)) for slot, env in BANKR_KEY_SLOTS.items()}
        return {a: configured[cls.agent_slot(a)] for a in AGENT_BANKR_KEYS}

    @classmethod
    def configured_wallet_slots(cls) -> dict[int, bool]:
        return {slot: bool(os.getenv(env)) for slot, env in BANKR_KEY_SLOTS.items()}

    def verify_agent(self, agent: str, timeout: int = 20) -> BankrAuthResult:
        agent = agent.upper()
        env_name = self.credential_env(agent)
        key = os.getenv(env_name)
        if not key:
            return BankrAuthResult(agent, False, False, error=f"{env_name} is not configured")
        req = urllib.request.Request(
            self.AUTH_ENDPOINT,
            headers={"Accept": "application/json", "X-API-Key": key},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
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
                return BankrAuthResult(agent, True, 200 <= response.status < 300, response.status, address)
        except urllib.error.HTTPError as exc:
            return BankrAuthResult(agent, True, False, exc.code, error=f"HTTP {exc.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return BankrAuthResult(agent, True, False, error=f"{type(exc).__name__}: {exc}")

    def verify_all_agents(self, timeout: int = 20) -> list[BankrAuthResult]:
        # One check per wallet slot avoids sending 100 duplicate auth requests.
        results = []
        for slot in BANKR_KEY_SLOTS:
            results.append(self.verify_agent(f"A{slot:03d}", timeout))
        return results

    def recent_symbols(self, timeout: int = 10) -> set[str]:
        req = urllib.request.Request(self.LAUNCHES_ENDPOINT, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = json.loads(response.read().decode())
            launches = body.get("launches", body if isinstance(body, list) else [])
            return {self.normalize_symbol(x.get("tokenSymbol", "")) for x in launches if isinstance(x, dict)}
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
            return set()

    def deployments_today(self, agent: str, now: float | None = None) -> int:
        now = time.time() if now is None else now
        cutoff = now - 86400
        slot = self.agent_slot(agent)
        env_name = BANKR_KEY_SLOTS[slot]
        count = 0
        try:
            with open(self.audit_path, encoding="utf-8") as handle:
                for line in handle:
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    item_agent = str(item.get("agent", ""))
                    item_slot = item.get("bankr_slot")
                    if item_slot is None and re.fullmatch(r"A\d{3}", item_agent):
                        item_slot = self.agent_slot(item_agent)
                    if item_slot == slot and item.get("status") == "deployed" and float(item.get("created_at", 0)) >= cutoff:
                        count += 1
        except OSError:
            pass
        return count

    def plan(self, agent, name, symbol, thesis, score, chain="robinhood"):
        agent = agent.upper()
        # Validate the agent before touching credentials or audit state.
        slot = self.agent_slot(agent)
        chain = chain.lower()
        if chain not in {"base", "robinhood"}:
            raise ValueError("Bankr token launch chain must be base or robinhood")
        plan = TokenPlan(agent, name[:100], self.normalize_symbol(symbol), chain, thesis[:500], float(score), created_at=time.time())
        self._audit(plan, bankr_slot=slot)
        return plan

    def creative_identity(self, agent: str, cycle: int, used_symbols: set[str] | None = None) -> tuple[str, str]:
        """Generate a deterministic, collision-resistant name/ticker for an agent."""
        used = used_symbols or set()
        slot = self.agent_slot(agent)
        idx = (cycle + int(agent[1:])) % len(NAME_WORDS)
        base_name = f"{NAME_WORDS[idx]} {slot}"
        base_symbol = self.normalize_symbol(f"{SYMBOL_WORDS[idx]}{slot}")
        symbol = base_symbol
        suffix = 0
        while symbol in used:
            suffix += 1
            symbol = self.normalize_symbol(f"{base_symbol}{suffix}")
        return base_name, symbol

    def simulate(self, plan: TokenPlan):
        result = TokenPlan(**asdict(plan))
        result.status = "simulated"
        self._audit(result, bankr_slot=self.agent_slot(plan.agent))
        return result

    def build_payload(self, plan: TokenPlan) -> dict:
        return {
            "tokenName": plan.name,
            "tokenSymbol": plan.symbol,
            "description": plan.thesis,
            "chain": plan.chain,
            # Fees stay with the launching Bankr wallet by default.
            "quoteOnlyFees": True,
            "simulateOnly": False,
        }

    def deploy(self, plan: TokenPlan):
        if not self.live:
            return self.simulate(plan)
        used = self.deployments_today(plan.agent)
        if used >= self.MAX_LAUNCHES_PER_WALLET:
            raise RuntimeError(f"Bankr launch quota reached for wallet slot {self.agent_slot(plan.agent)}: {used}/{self.MAX_LAUNCHES_PER_WALLET} in rolling 24h")
        key = os.getenv(self.credential_env(plan.agent))
        if not key:
            raise RuntimeError(f"{self.credential_env(plan.agent)} is required for live deployment")
        payload_obj = self.build_payload(plan)
        req = urllib.request.Request(
            self.ENDPOINT,
            data=json.dumps(payload_obj).encode(),
            headers={"Content-Type": "application/json", "Accept": "application/json", "X-API-Key": key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Bankr deployment failed: HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Bankr deployment failed: {type(exc).__name__}: {exc}") from exc
        result = TokenPlan(**asdict(plan))
        result.status = "deployed"
        result.token_address = str(body.get("tokenAddress", body.get("token_address", "")))
        result.tx_hash = str(body.get("txHash", body.get("tx_hash", "")))
        self._audit(result, bankr_slot=self.agent_slot(plan.agent))
        return result

    def autonomous_deploy(self, civilization, cycle: int, max_deploys: int = 4, chain: str | None = None) -> list[TokenPlan]:
        """Let surviving research agents launch tokens, never move wallet funds.

        At most one launch is attempted per wallet slot in a cycle. The Bankr
        service enforces its own per-wallet launch quota; this scheduler also
        enforces the same ceiling locally and stops once all four slots are used.
        """
        if not (self.live and self.auto_deploy):
            return []
        candidates = sorted(
            (idea for idea in civilization.global_ideas if idea.validation_passed),
            key=lambda idea: (idea.validation_score, idea.fitness),
            reverse=True,
        )
        launched: list[TokenPlan] = []
        used_symbols = self.recent_symbols()
        used_slots: set[int] = set()
        for idea in candidates:
            if len(launched) >= max(0, min(int(max_deploys), 4)):
                break
            slot = self.agent_slot(idea.origin)
            if slot in used_slots or self.deployments_today(idea.origin) >= self.MAX_LAUNCHES_PER_WALLET:
                continue
            name, symbol = self.creative_identity(idea.origin, cycle, used_symbols)
            used_symbols.add(symbol)
            selected_chain = (chain or os.getenv("BANKR_DEFAULT_CHAIN", "robinhood")).lower()
            plan = self.plan(idea.origin, name, symbol, idea.thesis, idea.validation_score, selected_chain)
            try:
                deployed = self.deploy(plan)
                launched.append(deployed)
                used_slots.add(slot)
            except Exception as exc:
                failed = TokenPlan(**asdict(plan)); failed.status = "failed"; self._audit(failed, bankr_slot=slot, error=f"{type(exc).__name__}: {exc}")
        return launched

    def _audit(self, plan, **extra):
        record = asdict(plan)
        record.update(extra)
        with open(self.audit_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def snapshot(self):
        return {
            "live": self.live,
            "auto_deploy": self.auto_deploy,
            "audit_path": self.audit_path,
            "wallet_slots": self.configured_wallet_slots(),
            "configured_agents": self.configured_agents(),
            "max_launches_per_wallet": self.MAX_LAUNCHES_PER_WALLET,
        }
