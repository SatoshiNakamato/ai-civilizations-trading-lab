from __future__ import annotations

from dataclasses import dataclass
from time import time
from .core import Civilization
from .knowledge_graph import KnowledgeGraph
from .research_coordinator import ResearchCoordinator
from .you_mcp import YouMCPResearch


@dataclass
class ResearchRuntimeStats:
    submitted: int = 0
    deduplicated: int = 0
    completed: int = 0
    failed: int = 0
    cache_hits: int = 0
    provider_calls: int = 0


class ResearchRuntime:
    """Governed research layer around the existing civilization loop.

    External research is optional: the civilization can keep running when the
    MCP SDK/network is unavailable. Successful findings are shared through the
    knowledge graph and repeated questions are served from cache.
    """

    def __init__(self, civilization: Civilization | None = None,
                 researcher: YouMCPResearch | None = None):
        self.civilization = civilization or Civilization()
        self.coordinator = ResearchCoordinator()
        self.researcher = researcher or YouMCPResearch()
        self.knowledge_graph = KnowledgeGraph()
        self.stats = ResearchRuntimeStats()
        self.started_at = time()

    def queue_agent_requests(self):
        before_count = len(self.coordinator.tasks)
        for agent in self.civilization.agents.values():
            question = self.civilization._research_query(agent)
            before = len(self.coordinator.tasks)
            self.coordinator.submit(question, agent.agent_id, agent.archetype, agent.curiosity)
            self.stats.submitted += 1
            if len(self.coordinator.tasks) == before:
                self.stats.deduplicated += 1
        return {"new_tasks": len(self.coordinator.tasks) - before_count,
                "coordinator": self.coordinator.snapshot()}

    def _share(self, task, results):
        finding_id = f"research:{task.task_id}"
        self.knowledge_graph.add(finding_id, "research", {
            "question": task.question,
            "topic": task.topic,
            "requester": task.requester,
            "results": [r.__dict__ for r in results],
        })
        self.knowledge_graph.add(f"agent:{task.requester}", "agent")
        self.knowledge_graph.link(f"agent:{task.requester}", finding_id, "researched")

    def drain(self, max_tasks: int = 10):
        processed = []
        for _ in range(max(0, int(max_tasks))):
            task = self.coordinator.next_task()
            if task is None:
                break
            try:
                cached = self.researcher.cached(task.question)
                if cached is not None:
                    self.stats.cache_hits += 1
                    results = cached
                else:
                    if not self.researcher.can_search():
                        task.status = "queued"
                        break
                    results = self.researcher.search(task.question)
                    self.stats.provider_calls += 1
                self._share(task, results)
                self.coordinator.complete(task.task_id, f"research-results:{len(results)}")
                self.stats.completed += 1
                processed.append(task)
            except Exception:
                task.status = "failed"
                self.stats.failed += 1
        return processed

    def cycle(self, max_research_tasks: int = 10):
        queued = self.queue_agent_requests()
        drained = self.drain(max_research_tasks)
        state = self.civilization.step()
        return {
            "civilization": state,
            "research_runtime": {
                "coordinator": self.coordinator.snapshot(),
                "stats": self.stats.__dict__.copy(),
                "drained": len(drained),
                "queued_before_cycle": queued,
                "knowledge_graph": self.knowledge_graph.snapshot(),
                "you": self.researcher.snapshot(),
            },
        }

    def snapshot(self):
        return {
            "coordinator": self.coordinator.snapshot(),
            "stats": self.stats.__dict__.copy(),
            "knowledge_graph": self.knowledge_graph.snapshot(),
            "you": self.researcher.snapshot(),
            "civilization": self.civilization.snapshot(),
        }
