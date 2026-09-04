from pathlib import Path
from civilizations.research_coordinator import ResearchCoordinator
from civilizations.research_quality import ResearchQuality
from civilizations.contradictions import ContradictionDetector
from civilizations.research_observability import ResearchObservability


def test_research_dedup_and_priority():
    r = ResearchCoordinator()
    a = r.submit("BTC outlook", "A001", "macro", .9)
    b = r.submit(" btc   outlook ", "A002", "macro", .1)
    assert a.task_id == b.task_id
    assert r.next_task().requester == "A001"


def test_quality_scoring():
    q = ResearchQuality()
    q.record("f1", "helpful")
    q.record("f1", "harmful")
    assert q.score("f1") == 0.0


def test_contradiction_detector():
    d = ContradictionDetector()
    found = d.compare("btc", ["BTC likely rise", "BTC likely decline"])
    assert found
    assert d.snapshot()["count"] == 1


def test_observability():
    o = ResearchObservability()
    s = o.cycle(cache_hits=3, completed=2)
    assert s["cycles"] == 1
    assert s["metrics"]["cache_hits"] == 3
