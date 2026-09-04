from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from time import time
import re

@dataclass
class ResearchTask:
    task_id: str
    question: str
    topic: str
    priority: float
    requester: str
    status: str = 'queued'
    created_at: float = 0.0
    result: str = ''

class ResearchCoordinator:
    def __init__(self):
        self.tasks = {}
        self.completed = {}

    @staticmethod
    def normalize_question(question: str) -> str:
        return re.sub(r'\s+', ' ', str(question).strip().lower())

    def submit(self, question, requester, topic='general', priority=0.5):
        normalized = self.normalize_question(question)
        key = sha256(normalized.encode()).hexdigest()[:16]
        if key in self.completed:
            return self.completed[key]
        if key in self.tasks:
            existing = self.tasks[key]
            existing.priority = max(existing.priority, max(0, min(1, priority)))
            return existing
        cleaned = ' '.join(str(question).strip().split())
        t = ResearchTask(key, cleaned, topic, max(0,min(1,priority)), requester, created_at=time())
        self.tasks[key] = t
        return t

    def next_task(self):
        q=[t for t in self.tasks.values() if t.status=='queued']
        if not q: return None
        t=max(q,key=lambda x:(x.priority, -x.created_at)); t.status='running'; return t

    def complete(self, task_id, result):
        t=self.tasks[task_id]; t.result=result; t.status='completed'; self.completed[task_id]=t; return t

    def snapshot(self):
        return {'queued':sum(t.status=='queued' for t in self.tasks.values()),'running':sum(t.status=='running' for t in self.tasks.values()),'completed':len(self.completed)}
