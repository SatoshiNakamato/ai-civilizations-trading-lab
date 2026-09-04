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
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, OSError) as exc: return ProviderResponse("you", False, error=f"{type(exc).__name__}: {exc}")

class AgentRouterAdapter:
    """Anthropic-compatible AgentRouter adapter."""
    def __init__(self, manager: ProviderManager | None = None):
        self.manager = manager or ProviderManager()
        self.base_url = (os.getenv("ANTHROPIC_BASE_URL") or "https://co.agentrouter.org").rstrip("/")
        self.model = os.getenv("ANTHROPIC_MODEL") or "claude-opus-4-6"
    def reason(self, agent_id: str, prompt: str) -> ProviderResponse:
        auth = self.manager.authorize(agent_id, "deep_reasoning")
        if not auth.get("allowed"): return ProviderResponse("agentrouter", False, error=auth.get("reason", "not_authorized"))
        try:
            data = _post_json(self.base_url + "/v1/messages", {"Authorization": f"Bearer {self.manager.credential_for('agentrouter') or ''}", "anthropic-version": "2023-06-01", "Content-Type": "application/json"}, {"model": self.model, "max_tokens": 256, "messages": [{"role": "user", "content": prompt[:40000]}]})
            blocks = data.get("content", []) or []
            content = "\n".join(str(b.get("text", "")) for b in blocks if isinstance(b, dict) and b.get("type") == "text")
            return ProviderResponse("agentrouter", True, content)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, OSError) as exc: return ProviderResponse("agentrouter", False, error=f"{type(exc).__name__}: {exc}")

class CognitiveGateway:
    """Only assigned agents can request external cognition through the budget gate."""
    def __init__(self, manager: ProviderManager | None = None):
        self.manager = manager or ProviderManager(); self.agentrouter = AgentRouterAdapter(self.manager); self.you = YouResearchAdapter(self.manager)
    def elite_reason(self, agent_id: str, prompt: str) -> ProviderResponse:
        return self.agentrouter.reason(agent_id, prompt) if agent_id == "A001" else ProviderResponse("agentrouter", False, error="agent_not_assigned")
    def research(self, agent_id: str, question: str) -> ProviderResponse:
        return self.you.research(agent_id, question, "lite") if agent_id == "A002" else ProviderResponse("you", False, error="agent_not_assigned")
    def snapshot(self) -> dict: return self.manager.snapshot()
