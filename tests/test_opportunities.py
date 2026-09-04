from civilizations.opportunities import Opportunity, OpportunityEngine


def good(**kw):
    base = dict(opportunity_id="", category="arbitrage", asset="BTC", summary="BTC venue spread", confidence=.95, risk=.1, gross_edge=.025, fees=.004, slippage=.003, liquidity=.9, sources=["https://example.com"], agents=["A001", "A002"], buy_venue="BUY", sell_venue="SELL")
    base.update(kw)
    return Opportunity(**base)


def test_arbitrage_net_edge_and_validation(tmp_path):
    e = OpportunityEngine(str(tmp_path / "audit.jsonl"))
    o = e.discover(good())
    assert o is not None
    assert abs(o.net_edge - .018) < 1e-9
    o = e.validate(o)
    assert o.status == "validated"
    assert o.score > .8


def test_rejects_weak_edge(tmp_path):
    e = OpportunityEngine(str(tmp_path / "audit.jsonl"))
    o = e.discover(good(gross_edge=.006, fees=.004, slippage=.003))
    assert e.validate(o).status == "rejected"


def test_dedup_and_alert(tmp_path):
    e = OpportunityEngine(str(tmp_path / "audit.jsonl"), cooldown_seconds=9999)
    o = e.discover(good())
    assert e.discover(good()) is None
    e.validate(o)
    assert e.should_alert(o) in {"HIGH", "CRITICAL"}
    assert e.snapshot()["stats"]["deduplicated"] == 1


def test_audit_trail(tmp_path):
    path = tmp_path / "audit.jsonl"
    e = OpportunityEngine(str(path))
    o = e.discover(good())
    e.validate(o)
    assert path.exists()
    assert len(path.read_text().splitlines()) >= 2
