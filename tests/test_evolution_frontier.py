from civilizations.evolution_frontier import EvolutionFrontier
from civilizations.evolution_governor import EvolutionGovernor, EvolutionGovernorConfig


def test_frontier_memory_experiment_genealogy_and_replay(tmp_path):
    governor = EvolutionGovernor(EvolutionGovernorConfig(workspace=tmp_path / "evolution"))
    frontier = EvolutionFrontier(governor=governor)
    frontier.remember_research(1, "a1", "test", "evidence", 0.8)
    frontier.record_experiment(1, "a1", "hypothesis", "accepted", 0.9)
    frontier.record_genealogy(1, "a1", ["a2", "a2"], "adoption")
    result = frontier.diagnose(1, ["a1"], 1, 1)
    assert result["status"] == "healthy"
    assert len(frontier.replay()) == 3


def test_frontier_mutation_is_governed(tmp_path):
    governor = EvolutionGovernor(EvolutionGovernorConfig(workspace=tmp_path / "evolution"))
    frontier = EvolutionFrontier(governor=governor)
    frontier.propose_mutation(5, "a1", "Improve strategy", "better evidence", "# proposal")
    files = governor.list("proposal", "a1")
    assert len(files) == 1
    payload = governor.read("proposal", files[0])
    assert '"requires_human_review": true' in payload


def test_command_snapshot_exposes_governance(tmp_path):
    governor = EvolutionGovernor(EvolutionGovernorConfig(workspace=tmp_path / "evolution"))
    frontier = EvolutionFrontier(governor=governor)
    snapshot = frontier.command_snapshot(2, frontier.diagnose(2, ["a1"], 1, 1), {}, 3)
    assert snapshot["constitution"]["source_write"] is False
    assert snapshot["generation"] == 3
