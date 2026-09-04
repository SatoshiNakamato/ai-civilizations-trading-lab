"""Safe Bankr token-launch preflight.

This command never broadcasts a transaction. It authenticates configured agents
and exercises Bankr's simulateOnly=true launch path so eligibility/auth problems
can be diagnosed before enabling live deployment.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from markets.bankr_token_agent import AGENT_BANKR_KEYS, BankrTokenAgent


def simulate(agent: BankrTokenAgent, agent_id: str, chain: str = "base") -> dict:
    env_name = agent.credential_env(agent_id)
    key = os.getenv(env_name)
    if not key:
        return {"agent": agent_id, "configured": False, "ok": False, "error": f"{env_name} is not configured"}

    plan = agent.plan(
        agent_id,
        "Bankr Preflight Token",
        "PREFLT",
        "Integration preflight; simulation only; no transaction should be broadcast.",
        0.0,
        chain,
    )
    # Do not call agent.deploy(): that path sets simulateOnly=false in live mode.
    payload = {
        "tokenName": plan.name,
        "tokenSymbol": plan.symbol,
        "description": plan.thesis,
        "chain": plan.chain,
        "quoteOnlyFees": True,
        "simulateOnly": True,
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json", **agent._auth_headers(key)}
    if key.strip().startswith("bk_ptr_"):
        recipient = os.getenv("BANKR_FEE_RECIPIENT", "").strip()
        if not recipient:
            return {"agent": agent_id, "configured": True, "ok": False, "error": "BANKR_FEE_RECIPIENT is required for partner-key simulation"}
        payload["feeRecipient"] = {"type": "wallet", "value": recipient}

    req = urllib.request.Request(agent.ENDPOINT, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            body = json.loads(response.read().decode())
        return {
            "agent": agent_id,
            "configured": True,
            "ok": True,
            "status_code": getattr(response, "status", 200),
            "chain": body.get("chain", chain),
            "predicted_token_address": body.get("tokenAddress", ""),
            "simulated": body.get("simulated", True),
        }
    except urllib.error.HTTPError as exc:
        return {"agent": agent_id, "configured": True, "ok": False, "status_code": exc.code, "error": agent._error_detail(exc)}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"agent": agent_id, "configured": True, "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    agent = BankrTokenAgent("data/bankr_preflight.jsonl", live=True)
    results = []
    for agent_id in AGENT_BANKR_KEYS:
        auth = agent.verify_agent(agent_id)
        item = {"agent": agent_id, "configured": auth.configured, "authenticated": auth.authenticated, "status_code": auth.status_code, "account_address": auth.account_address, "auth_error": auth.error}
        if auth.authenticated:
            item["simulation"] = simulate(agent, agent_id)
        else:
            item["simulation"] = {"ok": False, "error": "skipped because authentication failed"}
        results.append(item)
        print(json.dumps(item, sort_keys=True))

    return 0 if all(x["authenticated"] and x["simulation"].get("ok") for x in results if x["configured"]) else 1


if __name__ == "__main__":
    sys.exit(main())
