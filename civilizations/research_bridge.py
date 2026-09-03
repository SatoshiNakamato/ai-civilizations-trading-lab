from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .research import PublicWebCollector, ResearchDesk


@dataclass
class ResearchInsight:
    topic: str
    source: str
    excerpt: str
    relevance: float
    url: str = ""


class ResearchBridge:
    """Turns bounded, read-only research into agent context."""

    def __init__(self, desk: ResearchDesk, web_collector: PublicWebCollector | None = None):
        self.desk = desk
        self.web_collector = web_collector

    def search_for_agent(self, agent_id: str, query: str, limit: int = 5) -> list[ResearchInsight]:
        hits = self.desk.search(query, limit=limit)
        if not hits and self.web_collector is not None:
            self.desk.web_collector = self.web_collector
            try:
                self.desk.web_search_and_ingest(query, limit=limit)
                hits = self.desk.search(query, limit=limit)
            except Exception as exc:
                self.desk.ingest("research-error", "collector error", str(exc))
        return [
            ResearchInsight(topic=query, source=document.source, excerpt=document.text[:1500], relevance=1.0, url=document.url)
            for document in hits
        ]

    def build_context(self, agent_id: str, query: str, limit: int = 5) -> dict[str, Any]:
        insights = self.search_for_agent(agent_id, query, limit)
        return {
            "agent_id": agent_id,
            "query": query,
            "sources": [{"source": x.source, "relevance": x.relevance, "excerpt": x.excerpt, "url": x.url} for x in insights],
            "rule": "Research is evidence, not truth; agents must challenge and validate claims.",
        }
