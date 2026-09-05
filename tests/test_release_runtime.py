import pytest

from civilizations.execution import GuardedExecution, OrderIntent, PaperExecution
from civilizations.memory import CivilizationMemory, MemoryItem
from civilizations.scheduler import CivilizationScheduler, ScheduleConfig
from civilizations.state import StateSnapshot, StateStore


def test_state_store_round_trip(tmp_path):
    store = StateStore(tmp_path)
    store.save(StateSnapshot(2, "run-2", {"children": ["CIV-A.g3.1"]}))
    assert store.load() == StateSnapshot(2, "run-2", {"children": ["CIV-A.g3.1"]})


def test_memory_is_bounded():
    memory = CivilizationMemory(2)
    for i in range(3):
        memory.remember(MemoryItem(1, f"k{i}", str(i)))
    assert memory.keys() == ("k1", "k2")


def test_scheduler_can_be_bounded():
    calls = []
    assert CivilizationScheduler(lambda: calls.append(1), ScheduleConfig(0, 3)).run() == 3
    assert len(calls) == 3


def test_paper_execution_is_available():
    adapter = PaperExecution()
    assert adapter.submit(OrderIntent("CIV-A", "BTCUSDT", "buy", 1)) == "paper-00000001"


def test_live_execution_is_explicitly_disabled():
    adapter = GuardedExecution(PaperExecution())
    with pytest.raises(PermissionError, match="disabled"):
        adapter.submit(OrderIntent("CIV-A", "BTCUSDT", "buy", 1))
