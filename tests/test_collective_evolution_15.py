from civilizations.agent_communication import AgentCommunicationBus, CommunicationConfig
from civilizations.collective_evolution import CollectiveEvolutionLoop
from civilizations.evolution_frontier import EvolutionFrontier
from civilizations.evolution_governor import EvolutionGovernor, EvolutionGovernorConfig
from civilizations.learning_communication import CollectiveLearning


class FakePlatform:
    def __init__(self):
        self.experiments = []
        self.learned = []

    def experiment(self, agent, hypothesis, tick):
        self.experiments.append((agent, hypothesis, tick))
        return {"agent": agent, "hypothesis": hypothesis, "score": 0.8, "repeatable": True}

    def learn(self, agent, topic, evidence, confidence, tick):
        self.learned.append((agent, topic, evidence, confidence, tick))


def test_fifteen_stage_cycle_is_complete(tmp_path):
    bus = AgentCommunicationBus(CommunicationConfig(root=tmp_path / "communication"))
    collective = CollectiveLearning(bus, seed=7)
    governor = EvolutionGovernor(EvolutionGovernorConfig(workspace=tmp_path / "evolution"))
    frontier = EvolutionFrontier(governor=governor, root=tmp_path / "evolution" / "frontier")
    platform = FakePlatform()
    loop = CollectiveEvolutionLoop(bus, collective, frontier, platform)

    agents = [f"A{i:03d}" for i in range(6)]
    evidence = {aid: f"{aid} found reproducible evidence about a bounded research hypothesis." for aid in agents}
    result = loop.run(agents, tick=5, evidence=evidence, active_ids=agents)

    assert result["complete"] is True
    assert len(result["stages"]) == 15
    assert [stage["number"] for stage in result["stages"]] == list(range(1, 16))
    assert result["research_exchanges"] == len(agents)
    assert result["debates"] == len(agents)
    assert result["experiments"] > 0
    assert result["genealogy_records"] > 0
    assert result["mutation_proposals"] == 1
    assert len(platform.experiments) == result["experiments"]
    assert governor.list("proposal")


def test_cycle_is_bounded_and_non_empty_population_is_required(tmp_path):
    bus = AgentCommunicationBus(CommunicationConfig(root=tmp_path / "communication"))
    collective = CollectiveLearning(bus)
    governor = EvolutionGovernor(EvolutionGovernorConfig(workspace=tmp_path / "evolution"))
    frontier = EvolutionFrontier(governor=governor, root=tmp_path / "evolution" / "frontier")
    loop = CollectiveEvolutionLoop(bus, collective, frontier, FakePlatform())

    result = loop.run(["A", "B"], tick=1, evidence={"A": "evidence", "B": "evidence"}, active_ids=["A"])
    assert result["complete"] is True
    assert result["active_agents"] == 1
    assert result["mutation_proposals"] == 0
