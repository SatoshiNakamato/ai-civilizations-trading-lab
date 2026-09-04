from markets.end_to_end import TradingCivilizationV1


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
