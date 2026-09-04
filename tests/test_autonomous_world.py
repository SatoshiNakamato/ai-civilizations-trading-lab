from simulation.autonomous_world import AutonomousWorld

class FakeCivilization:
    def __init__(self): self.n = 0
    def cycle(self):
        self.n += 1
        return {"cycle": self.n}
    def snapshot(self): return {"cycles": self.n}

def test_world_runs_bounded_cycles():
    c = FakeCivilization()
    sleeps = []
    w = AutonomousWorld(c, interval_seconds=5, sleeper=sleeps.append)
    assert w.run(max_cycles=3) == 3
    assert w.cycles == 3
    assert sleeps == [5, 5]
    assert not w.running

def test_world_stop_state():
    c = FakeCivilization()
    w = AutonomousWorld(c, sleeper=lambda _: None)
    assert w.snapshot()["running"] is False
    w.stop()
    assert w.snapshot()["running"] is False
