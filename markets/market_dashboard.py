from __future__ import annotations

import json
from .civilization_market_hub import CivilizationMarketHub


def render_dashboard(hub: CivilizationMarketHub) -> str:
    d = hub.dashboard()
    lines = ["CIVILIZATION MARKET INTELLIGENCE", "=" * 34, f"Mode: {d['mode']}", f"Execution enabled: {d['execution_enabled']}", "", "Opportunity memory:"]
    lines.append(json.dumps(d["opportunity_memory"], indent=2))
    lines.append("\nAgent reputation:")
    if d["agent_scores"]:
        for a in d["agent_scores"]:
            lines.append(f"{a['agent_id']}: reputation={a['reputation']:.3f} accuracy={a['accuracy']:.3f} observations={a['observations']}")
    else:
        lines.append("No verified agent predictions yet.")
    lines.append("\nHypothesis feedback:")
    lines.append(json.dumps(d["hypothesis_feedback"], indent=2))
    lines.append(f"\nEvents recorded: {d['events']}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_dashboard(CivilizationMarketHub()))
