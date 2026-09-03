from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CognitiveMemory:
    entries: list[dict[str, Any]] = field(default_factory=list)

    def add(self, role: str, text: str) -> None:
        self.entries.append({"role": role, "text": text})
        self.entries = self.entries[-40:]


class WebResearch:
    """Read-only public web research through an approved HTTP endpoint.

    Set RESEARCH_URL to a service you control. The endpoint should accept
    ?q=<query> and return JSON: {"results": [{"title","url","snippet"}, ...]}.
    This layer never executes trades or financial actions.
    """

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.getenv("RESEARCH_URL", "")

    def search(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        if not self.base_url:
            return []
        params = urllib.parse.urlencode({"q": query, "limit": limit})
        url = f"{self.base_url.rstrip('?&')}&{params}" if "?" in self.base_url else f"{self.base_url}?{params}"
        request = urllib.request.Request(url, headers={"User-Agent": "AI-Civilizations-Lab/1.0"})
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("results", [])[:limit]


class CognitiveAgent:
    """LLM-backed cognitive interface for a simulated citizen.

    The model provider is intentionally externalized through a small adapter.
    No wallet signing, order submission, or autonomous financial execution is
    exposed here.
    """

    def __init__(self, agent, model_call=None, web_research: WebResearch | None = None):
        self.agent = agent
        self.model_call = model_call
        self.web = web_research or WebResearch()
        self.memory = CognitiveMemory()

    def respond(self, message: str, research: bool = False) -> str:
        self.memory.add("user", message)
        sources = self.web.search(message) if research else []

        context = {
            "agent_id": self.agent.agent_id,
            "specialization": self.agent.archetype,
            "intelligence": self.agent.intelligence.profile(),
            "memory": self.memory.entries[-20:],
            "research": sources,
            "instruction": (
                "Answer the user's question directly. Distinguish facts, "
                "hypotheses and uncertainty. Never claim web access or research "
                "that did not occur. This is a simulated research agent and "
                "cannot execute financial transactions."
            ),
        }

        if self.model_call is None:
            answer = self._local_fallback(message, sources)
        else:
            answer = self.model_call(context)

        self.memory.add("agent", answer)
        return answer

    def _local_fallback(self, message: str, sources: list[dict[str, str]]) -> str:
        source_note = " I found no configured web sources." if not sources else f" I found {len(sources)} web research results."
        return (
            f"{self.agent.agent_id}: I understand your question as: {message}. "
            f"My specialization is {self.agent.archetype}; capability is "
            f"{self.agent.intelligence.capability_score:.3f}."
            f"{source_note} I need an LLM provider for open-ended reasoning."
        )
