from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CognitiveMemory:
    entries: list[dict[str, Any]] = field(default_factory=list)

    def add(self, role: str, text: str) -> None:
        self.entries.append({"role": role, "text": text})
        self.entries = self.entries[-40:]


class OpenAIResponses:
    """Dependency-free OpenAI Responses API adapter with read-only web search."""

    def __init__(self, model: str | None = None):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
        self.endpoint = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/responses")

    def __call__(self, context: dict[str, Any]) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        body = {
            "model": self.model,
            "tools": [{"type": "web_search"}],
            "input": [
                {"role": "system", "content": (
                    "You are one citizen inside a simulated AI civilization. "
                    "Reason independently, use persistent memory, challenge weak claims, "
                    "and communicate naturally. Use web search for current or external "
                    "information when useful. Separate sourced facts from hypotheses. "
                    "You may research markets, arbitrage, prediction markets and new assets, "
                    "but never execute trades, move money, sign transactions, control wallets, "
                    "or claim guaranteed profits."
                )},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False, indent=2)},
            ],
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "User-Agent": "AI-Civilizations-Lab/1.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API error {exc.code}: {detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI network error: {exc.reason}") from exc
        if payload.get("output_text"):
            return payload["output_text"].strip()
        chunks = []
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    chunks.append(content["text"])
        if chunks:
            return "\n".join(chunks).strip()
        raise RuntimeError("OpenAI response contained no text output")


class CognitiveAgent:
    """LLM-backed cognitive interface for a simulated citizen."""

    def __init__(self, agent, model_call=None):
        self.agent = agent
        self.model_call = model_call or OpenAIResponses()
        self.memory = CognitiveMemory()

    def respond(self, message: str) -> str:
        self.memory.add("user", message)
        context = {
            "agent_id": self.agent.agent_id,
            "name": self.agent.name,
            "specialization": self.agent.archetype,
            "personality": {"risk_tolerance": self.agent.risk_tolerance, "curiosity": self.agent.curiosity, "cooperation": self.agent.cooperation},
            "intelligence": self.agent.intelligence.profile(),
            "current_beliefs": self.agent.beliefs,
            "recent_ideas": [{"title": i.title, "thesis": i.thesis, "fitness": i.fitness} for i in self.agent.ideas[-8:]],
            "memory": self.memory.entries[-20:],
            "user_message": message,
        }
        try:
            answer = self.model_call(context)
        except RuntimeError as exc:
            answer = f"I cannot reach my cognitive model right now: {exc}. My local simulation state is still available."
        self.memory.add("agent", answer)
        return answer
