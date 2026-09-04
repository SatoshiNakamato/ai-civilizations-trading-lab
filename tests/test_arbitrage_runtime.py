from civilizations.live_arbitrage import Quote
from markets.arbitrage_runtime import ArbitrageRuntime

class FakeScanner:
    def __init__(self, opportunity): self.opportunity=opportunity
    def scan_once(self): return self.opportunity
    def snapshot(self): return {"ok": True}

def test_scan_open_observe_close(tmp_path):
    from civilizations.opportunities import Opportunity
    o=Opportunity('opp','arbitrage','BTC','spread',.99,.1,.03,.002,.001,1,['x'],['A001'],'cheap','rich',100,103,'validated')
    r=ArbitrageRuntime(FakeScanner(o), __import__('markets.paper_execution',fromlist=['PaperExecutionEngine']).PaperExecutionEngine(str(tmp_path/'fills.jsonl')), __import__('markets.trader_leaderboard',fromlist=['TraderLeaderboard']).TraderLeaderboard())
    f=r.scan_and_open('A001'); assert f is not None
    r.close(f.fill_id,[Quote('cheap','BTC-USD',100,100.5),Quote('rich','BTC-USD',101.5,102)])
    assert r.paper.snapshot()['closed']==1
    assert r.leaderboard.snapshot()[0]['trades']==1
