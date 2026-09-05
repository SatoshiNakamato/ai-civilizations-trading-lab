from civilizations.agent_communication import AgentCommunicationBus, CommunicationConfig
from civilizations.learning_communication import CollectiveLearning


def test_collective_round_exchanges_all_agents(tmp_path):
    bus = AgentCommunicationBus(CommunicationConfig(root=tmp_path))
    collective = CollectiveLearning(bus=bus, seed=7)
    agents = [f"agent-{i}" for i in range(10)]
    evidence = {aid: f"finding from {aid}" for aid in agents}

    exchanges = collective.round(agents, tick=1, evidence=evidence)

    assert len(exchanges) == 10
    assert len(bus.log_path.read_text().splitlines()) == 10
    assert {x.sender for x in exchanges} == set(agents)
    assert all(x.sender != x.recipient for x in exchanges)


def test_debate_is_durable_and_audited(tmp_path):
    bus = AgentCommunicationBus(CommunicationConfig(root=tmp_path))
    collective = CollectiveLearning(bus=bus, seed=1)
    agents = ["agent-a", "agent-b", "agent-c"]

    debate = collective.debate(agents, tick=3, topic="arbitrage")

    assert len(debate) == 3
    assert len(bus.log_path.read_text().splitlines()) == 3
    assert len(bus.audit_path.read_text().splitlines()) == 3
    assert collective.snapshot()["messages"] == 0
