from markets.continuous_arbitrage import ContinuousArbitrage

class FakeRuntime:
    def __init__(self):
        self.n=0
    def scan_and_open(self, agent): return None
    def snapshot(self): return {"paper":{"realized_pnl":0.0},"leaderboard":[],"scanner":{}}

class FakeLeaderboard:
    def profitable(self,n=3): return []

def test_continuous_cycle_no_opportunity():
    r=FakeRuntime(); r.leaderboard=FakeLeaderboard()
    c=ContinuousArbitrage(runtime=r,agents=["A","B"])
    x=c.cycle()
    assert x.cycle==1 and x.opened==0 and x.closed==0 and x.realized_pnl==0

def test_cycle_snapshot():
    c=ContinuousArbitrage(runtime=FakeRuntime(),agents=["A"])
    c.cycle()
    s=c.snapshot()
    assert s["cycles"]==1 and "runtime" in s
