from civilizations.opportunities import Opportunity
from markets.paper_execution import PaperExecutionEngine

def test_lifecycle_and_realized_pnl(tmp_path):
    e=PaperExecutionEngine(str(tmp_path/'fills.jsonl'))
    o=Opportunity('x','arbitrage','BTC','spread',.95,.1,gross_edge=.02,fees=.001,slippage=.001,liquidity=1,sources=['x'],buy_venue='cheap',sell_venue='rich',buy_price=100,sell_price=102,status='validated')
    f=e.open(o,'A001',1); e.close(f.fill_id,101,101.5)
    assert f.status=='closed' and f.realized_pnl>0 and e.snapshot()['closed']==1

def test_only_paper(tmp_path):
    e=PaperExecutionEngine(str(tmp_path/'fills.jsonl'))
    assert e.snapshot()['open']==0
