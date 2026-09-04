from __future__ import annotations

from dataclasses import dataclass
from time import time
from .core import Civilization
from .research_coordinator import ResearchCoordinator

@dataclass
class ResearchRuntimeStats:
    submitted: int = 0
    deduplicated: int = 0
    completed: int = 0
    failed: int = 0

class ResearchRuntime:
    """Governed research layer around the existing civilization loop."""
    def __init__(self, civilization: Civilization | None = None):
        self.civilization = civilization or Civilization()
        self.coordinator = ResearchCoordinator()
        self.stats = ResearchRuntimeStats()
        self.started_at = time()

    def queue_agent_requests(self):
        for agent in self.civilization.agents.values():
            question = self.civilization._research_query(agent)
            before = len(self.coordinator.tasks)
            self.coordinator.submit(question, agent.agent_id, agent.archetype, agent.curiosity)
            self.stats.submitted += 1
            if len(self.coordinator.tasks) == before:
                self.stats.deduplicated += 1
        return self.coordinator.snapshot()

    def drain(self, max_tasks: int = 10):
        processed = []
        for _ in range(max(0, int(max_tasks))):
            task = self.coordinator.next_task()
            if task is None:
                break
            self.coordinator.complete(task.task_id, f"queued-for-provider:{task.topic}")
            self.stats.completed += 1
            processed.append(task)
        return processed

    def cycle(self, max_research_tasks: int = 10):
        before = self.queue_agent_requests()
        drained = self.drain(max_research_tasks)
        state = self.civilization.step()
        return {"civilization": state, "research_runtime": {"coordinator": self.coordinator.snapshot(), "stats": self.stats.__dict__.copy(), "drained": len(drained), "queued_before_cycle": before}}

    def snapshot(self):
        return {"coordinator": self.coordinator.snapshot(), "stats": self.stats.__dict__.copy(), "civilization": self.civilization.snapshot()}
