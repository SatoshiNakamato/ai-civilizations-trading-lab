from pathlib import Path

import pytest

from civilizations.evolution_governor import EvolutionGovernor, EvolutionGovernorConfig


def governor(tmp_path: Path) -> EvolutionGovernor:
    return EvolutionGovernor(EvolutionGovernorConfig(workspace=tmp_path))


def test_agent_can_persist_memory_in_its_namespace(tmp_path):
    g = governor(tmp_path)
    result = g.write("agent-07", "memory", "agent-07/lesson.json", '{"lesson":"wait for evidence"}')
    assert result.kind == "memory"
    assert g.read("memory", "agent-07/lesson.json") == '{"lesson":"wait for evidence"}'


def test_agents_cannot_escape_namespace(tmp_path):
    g = governor(tmp_path)
    with pytest.raises(ValueError):
        g.write("agent-07", "memory", "../../escape.txt", "x")
    with pytest.raises(ValueError):
        g.write("agent-07", "memory", "agent-07/../escape.txt", "x")


def test_source_change_is_a_proposal_not_a_source_write(tmp_path):
    g = governor(tmp_path)
    result = g.propose_source_change(
        "agent-12",
        "better evidence weighting",
        "reduce false positives after repeated out-of-sample failures",
        "diff --git a/civilizations/example.py b/civilizations/example.py\n...",
    )
    assert result.kind == "proposal"
    payload = g.read("proposal", result.path.removeprefix("world_artifacts/agent_proposals/"))
    assert '"requires_human_review": true' in payload
    assert '"source_write": false' in payload


def test_quotas_are_enforced(tmp_path):
    config = EvolutionGovernorConfig(workspace=tmp_path, max_file_bytes=10, max_total_bytes=20, max_files=2)
    g = EvolutionGovernor(config)
    with pytest.raises(ValueError):
        g.write("agent-1", "memory", "a.txt", "12345678901")
    g.write("agent-1", "memory", "a.txt", "1234567890")
    g.write("agent-1", "memory", "b.txt", "1234567890")
    with pytest.raises(RuntimeError):
        g.write("agent-1", "memory", "c.txt", "x")


def test_symlink_is_rejected(tmp_path):
    g = governor(tmp_path)
    base = tmp_path / g.NAMESPACES["memory"]
    base.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    link = base / "link.txt"
    link.symlink_to(outside)
    with pytest.raises(PermissionError):
        g.write("agent-1", "memory", "link.txt", "overwrite")
