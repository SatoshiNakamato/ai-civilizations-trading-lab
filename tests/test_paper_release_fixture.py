from release.paper_fixture import build_paper_release_fixture


def test_deterministic_paper_release_fixture_exercises_full_path(tmp_path):
    report = build_paper_release_fixture(str(tmp_path))

    assert report.ledger["valid"] is True
    assert report.ledger["trades"] == 4
    assert report.pnl["trades"] == 4
    assert report.pnl["net_pnl"] == 20.0
    assert report.attribution["trades"] == 4
    assert report.attribution["total_pnl"] == 20.0
    assert report.attribution["by_agent"]["A001"]["net_pnl"] == 12.0
    assert report.attribution["by_category"]["momentum"]["trades"] == 2
    assert report.backtest["validated"] is True
    assert report.backtest["windows"] == 3
    assert report.monitoring["health"] == "ok"
    assert report.monitoring["paper"]["trades_seen"] == 4
    assert report.monitoring["audit"]["events_seen"] == 4
