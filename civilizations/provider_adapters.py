from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .provider_manager import ProviderManager

@dataclass(frozen=True)
class ProviderResponse:
    provider: str
    ok: bool
    content: str = ""
    sources: list[dict[str, str]] = field(default_factory=list)
    error: str = ""

def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int = 45) -> dict[str, Any]:
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

class YouResearchAdapter:
    """Official You.com Research API adapter."""
    endpoint = "https://api.you.com/v1/research"
    def __init__(self, manager: ProviderManager | None = None): self.manager = manager or ProviderManager()
    def research(self, agent_id: str, question: str, effort: str = "lite") -> ProviderResponse:
        auth = self.manager.authorize(agent_id, "web_research")
        if not auth.get("allowed"): return ProviderResponse("you", False, error=auth.get("reason", "not_authorized"))
        try:
            data = _post_json(self.endpoint, {"X-API-Key": self.manager.credential_for("you") or "", "Content-Type": "application/json"}, {"input": question[:40000], "research_effort": effort})
            output = data.get("output", {})
            sources = [{"title": str(s.get("title", "")), "url": str(s.get("url", ""))} for s in (output.get("sources", []) or []) if isinstance(s, dict)]
            return ProviderResponse("you", True, str(output.get("content", "")), sources)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc: return ProviderResponse("you", False, error=f"{type(exc).__name__}: {exc}")

class AgentRouterAdapter:
    """OpenAI-compatible AgentRouter adapter; route/model are private configuration."""
    def __init__(self, manager: ProviderManager | None = None):
        self.manager = manager or ProviderManager(); self.base_url = os.getenv("AGENTROUTER_BASE_URL", "").rstrip("/"); self.model = os.getenv("AGENTROUTER_MODEL", "")
    def reason(self, agent_id: str, prompt: str) -> ProviderResponse:
        # Check configuration before reserving a billable call.
        if not self.base_url or not self.model: return ProviderResponse("agentrouter", False, error="AGENTROUTER_BASE_URL or AGENTROUTER_MODEL not configured")
        auth = self.manager.authorize(agent_id, "deep_reasoning")
        if not auth.get("allowed"): return ProviderResponse("agentrouter", False, error=auth.get("reason", "not_authorized"))
        try:
            data = _post_json(self.base_url + "/chat/completions", {"Authorization": f"Bearer {self.manager.credential_for('agentrouter') or ''}", "Content-Type": "application/json"}, {"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2})
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return ProviderResponse("agentrouter", True, str(content))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc: return ProviderResponse("agentrouter", False, error=f"{type(exc).__name__}: {exc}")

class CognitiveGateway:
    """Only assigned agents can request external cognition through the budget gate."""
    def __init__(self, manager: ProviderManager | None = None):
        self.manager = manager or ProviderManager(); self.agentrouter = AgentRouterAdapter(self.manager); self.you = YouResearchAdapter(self.manager)
    def elite_reason(self, agent_id: str, prompt: str) -> ProviderResponse:
        return self.agentrouter.reason(agent_id, prompt) if agent_id == "A001" else ProviderResponse("agentrouter", False, error="agent_not_assigned")
    def research(self, agent_id: str, question: str) -> ProviderResponse:
        return self.you.research(agent_id, question, "lite") if agent_id == "A002" else ProviderResponse("you", False, error="agent_not_assigned")
    def snapshot(self) -> dict: return self.manager.snapshot()
