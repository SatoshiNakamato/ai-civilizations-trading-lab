from civilizations.core import Civilization
from civilizations.emergence import EmergenceEngine


def test_emergence_forms_organizations_and_tracks_state():
    civilization = Civilization(size=20, seed=7)
    state = civilization.step()
    emergence = state["emergence"]
    assert emergence["memes"] >= 20
    assert emergence["organizations"] >= 1
    assert emergence["social_capital"] >= 0
    assert emergence["events"]


def test_strategy_mutations_are_bounded_data():
    engine = EmergenceEngine(seed=1)
    assert engine.snapshot()["organizations"] == 0
    assert engine.snapshot()["memes"] == 0
