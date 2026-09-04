from civilizations.cycle_telemetry import CycleTelemetry


def test_cycle_telemetry_records_all_stages(capsys):
    t = CycleTelemetry(3, 100)
    for stage in CycleTelemetry.STAGES:
        t.stage(stage, "ok", 1)
    snapshot = t.snapshot()
    assert snapshot["cycle"] == 3
    assert snapshot["agents"] == 100
    assert [x["stage"] for x in snapshot["stages"]] == list(CycleTelemetry.STAGES)
    t.log()
    out = capsys.readouterr().out
    assert "STAGE cycle=3 stage=research status=ok count=1" in out
    assert "STAGE cycle=3 stage=learning status=ok count=1" in out
