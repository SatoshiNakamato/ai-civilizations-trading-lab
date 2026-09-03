from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .research import ResearchDesk


@dataclass
class ResearchInsight:
    topic: str
    source: str
    excerpt: str
    relevance: float


class ResearchBridge:
    """Turns approved research-desk material into bounded agent insights."""

    def __init__(self, desk: ResearchDesk):
        self.desk = desk

    def search_for_agent(self, agent_id: str, query: str, limit: int = 5) -> list[ResearchInsight]:
        hits = self.desk.search(query, limit=limit)
        return [
            ResearchInsight(
                topic=query,
                source=document.source,
                excerpt=document.text[:1500],
                relevance=1.0,
            )
            for document in hits
        ]

    def build_context(self, agent_id: str, query: str, limit: int = 5) -> dict[str, Any]:
        insights = self.search_for_agent(agent_id, query, limit)
        return {
            "agent_id": agent_id,
            "query": query,
            "sources": [
                {"source": x.source, "relevance": x.relevance, "excerpt": x.excerpt}
                for x in insights
            ],
            "rule": "Research is evidence, not truth; agents must challenge and validate claims.",
        }
