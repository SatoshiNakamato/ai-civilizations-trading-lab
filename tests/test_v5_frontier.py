from civilizations.v5_frontier import V5_CAPABILITIES, V5Frontier


def test_v5_declares_twelve_capabilities():
    assert len(V5_CAPABILITIES) == 12
    assert [c.number for c in V5_CAPABILITIES] == list(range(1, 13))


def test_v5_frontier_is_complete_from_repository_root():
    report = V5Frontier(".").check()
    assert report["version"] == "5"
    assert report["complete"] is True
    assert all(item["ok"] for item in report["capabilities"])


def test_v5_assert_ready():
    V5Frontier(".").assert_ready()
