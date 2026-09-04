from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock

CONFIG_PATH = Path(os.getenv("AI_CIVILIZATION_CONFIG", "~/.config/ai-civilization/providers.env")).expanduser()
USAGE_PATH = Path(os.getenv("AI_CIVILIZATION_USAGE", "~/.local/state/ai-civilization/provider_usage.json")).expanduser()


@dataclass(frozen=True)
class ProviderPolicy:
    provider: str
    daily_calls: int
    enabled: bool = True


class ProviderManager:
    """Credential boundary and credit governor for external reasoning providers.

    API secrets stay outside the repository. Agents receive a provider decision,
    never the credential itself. Network calls are intentionally left to provider
    adapters so this class cannot accidentally spend credits by itself.
    """

    def __init__(self, usage_path: Path = USAGE_PATH):
        self.usage_path = usage_path
        self._lock = Lock()
        self.policies = {
            "A001": ProviderPolicy("agentrouter", 5),
            "A002": ProviderPolicy("you", 10),
        }
        self._usage = self._load_usage()

    @staticmethod
    def load_local_credentials(path: Path = CONFIG_PATH) -> dict[str, str]:
        """Load KEY=value/export KEY=value from the user's private config.

        Values are returned only to trusted provider adapters and are never
        included in snapshots or logs.
        """
        values: dict[str, str] = {}
        if path.exists():
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[7:].lstrip()
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                if key in {"AGENTROUTER_API_KEY", "YDC_API_KEY"} and value:
                    values[key] = value
        # Environment wins, without requiring secrets to live in a file.
        for key in ("AGENTROUTER_API_KEY", "YDC_API_KEY"):
            if os.getenv(key):
                values[key] = os.environ[key]
        return values

    def _load_usage(self) -> dict:
        try:
            data = json.loads(self.usage_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _save_usage(self) -> None:
        self.usage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.usage_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._usage, indent=2), encoding="utf-8")
        tmp.replace(self.usage_path)

    @staticmethod
    def _day() -> str:
        return time.strftime("%Y-%m-%d", time.localtime())

    def _credential_name(self, provider: str) -> str:
        return {"agentrouter": "AGENTROUTER_API_KEY", "you": "YDC_API_KEY"}[provider]

    def authorize(self, agent_id: str, task: str = "reasoning") -> dict:
        """Return a non-secret authorization decision and reserve one call."""
        policy = self.policies.get(agent_id)
        if not policy or not policy.enabled:
            return {"allowed": False, "reason": "no_external_provider_policy"}
        credentials = self.load_local_credentials()
        key_name = self._credential_name(policy.provider)
        if not credentials.get(key_name):
            return {"allowed": False, "reason": "credential_unavailable", "provider": policy.provider}
        with self._lock:
            day = self._day()
            bucket = self._usage.setdefault(day, {})
            used = int(bucket.get(agent_id, 0))
            if used >= policy.daily_calls:
                return {"allowed": False, "reason": "daily_budget_exhausted", "provider": policy.provider, "remaining": 0}
            bucket[agent_id] = used + 1
            self._save_usage()
            return {
                "allowed": True,
                "provider": policy.provider,
                "remaining": policy.daily_calls - used - 1,
                "task": task,
            }

    def credential_for(self, provider: str) -> str | None:
        """Trusted adapter hook; never put the returned value in logs/snapshots."""
        name = self._credential_name(provider)
        return self.load_local_credentials().get(name)

    def snapshot(self) -> dict:
        day = self._day()
        used = self._usage.get(day, {})
        return {
            "date": day,
            "policies": {agent: asdict(policy) for agent, policy in self.policies.items()},
            "usage": dict(used),
            "credentials_loaded": {
                "agentrouter": bool(self.load_local_credentials().get("AGENTROUTER_API_KEY")),
                "you": bool(self.load_local_credentials().get("YDC_API_KEY")),
            },
        }
