from civilizations.agent_communication import AgentCommunicationBus, CommunicationConfig
from civilizations.learning_communication import CollectiveLearning


def test_collective_evolution_cycle_has_research_synthesis_debate_and_adoption(tmp_path):
    bus = AgentCommunicationBus(CommunicationConfig(root=tmp_path))
    collective = CollectiveLearning(bus=bus, seed=11)
    agents = [f"agent-{i}" for i in range(12)]
    evidence = {aid: f"independent finding from {aid}" for aid in agents}

    cycle = collective.complete_cycle(agents, tick=6, evidence=evidence, topic="strategy research")

    assert cycle["agents"] == 12
    assert cycle["research_exchanges"] == 12
    assert cycle["debates"] == 12
    assert cycle["adopted"] == 12
    assert cycle["rejected"] == 0
    snapshot = collective.snapshot()
    assert snapshot["last_synthesis"]["independent_sources"] == 12
    assert snapshot["cycle_history"][-1]["debates"] == 12
    assert len(bus.log_path.read_text().splitlines()) == 24
    assert len(bus.audit_path.read_text().splitlines()) == 24
