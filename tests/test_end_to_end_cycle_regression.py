from markets.end_to_end import TradingCivilizationV1
from markets.portfolio import PaperExecutionEngine


class FakeResearch:
    def __init__(self):
        self.received_cycle = None

    def cycle(self, agents, cycle):
        self.received_cycle = cycle
        assert isinstance(cycle, int)
        return []

    def snapshot(self):
        return {}


class FakeBankr:
    live = False

    def recent_symbols(self):
        return set()

    def snapshot(self):
        return {"live": False}


def test_cycle_passes_integer_cycle_counter_not_bound_method():
    runtime = TradingCivilizationV1()
    research = FakeResearch()
    runtime.research = research
    runtime.bankr = FakeBankr()

    result = runtime.cycle()

    assert research.received_cycle == 1
    assert result["cycle"] == 1
    assert result["bankr_plans"] == []


def test_paper_execution_round_trip_tracks_pnl():
    engine = PaperExecutionEngine(initial_cash=100.0, max_position_notional=50.0)
    order = engine.open("A001", "TEST", 25.0, 1.0)
    assert order.status == "filled"
    assert engine.snapshot()["cash"] == 75.0

    engine.mark("A001", "TEST", 1.2)
    snap = engine.snapshot()
    assert round(snap["unrealized_pnl"], 6) == 5.0
    assert round(snap["equity"], 6) == 105.0

    closed = engine.close("A001", "TEST", 1.2)
    assert round(closed.realized_pnl, 6) == 5.0
    assert engine.snapshot()["open_positions"] == []
    assert round(engine.snapshot()["cash"], 6) == 105.0
