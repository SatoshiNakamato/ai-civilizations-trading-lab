import json
from pathlib import Path

import civilizations.background as background


def test_chat_returns_live_agent_replies(tmp_path):
    latest = tmp_path / "latest.json"
    latest.write_text(json.dumps({"tick": 1}), encoding="utf-8")
    old = background.LATEST
    background.LATEST = latest
    try:
        from civilizations.aeon_runtime import AEONRuntime
        from civilizations.autonomous_world import AutonomousWorld
        world = AutonomousWorld(AEONRuntime(), root=str(tmp_path / "world"))
        result = background._handle("chat hello", world)
        assert result["ok"] is True
        assert result["background_active"] is True
        assert len(result["replies"]) == 3
    finally:
        background.LATEST = old


def test_command_center_is_a_client_not_a_second_world():
    source = Path("civilizations/command_center.py").read_text(encoding="utf-8")
    assert "AutonomousWorld" not in source
    assert "from .background import submit" in source
