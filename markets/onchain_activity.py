from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class ChainActivity:
    chain: str
    block_or_slot: int
    observed_at: float
    source: str
    ok: bool
    detail: str


class OnChainActivity:
    """Minimal read-only chain telemetry; no wallets or transaction signing."""

    def __init__(self, timeout: int = 8):
        self.timeout = timeout

    def _post(self, url: str, payload: dict):
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "User-Agent": "ai-civilizations-trading-lab/1.0"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode())

    def evm_block(self, chain: str, rpc_url: str) -> ChainActivity:
        try:
            x = self._post(rpc_url, {"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]})
            if "result" not in x:
                return ChainActivity(chain, 0, time.time(), "EVM JSON-RPC", False, str(x.get("error", "missing result")))
            return ChainActivity(chain, int(x["result"], 16), time.time(), "EVM JSON-RPC", True, "latest block")
        except Exception as e:
            return ChainActivity(chain, 0, time.time(), "EVM JSON-RPC", False, str(e))

    def solana_slot(self, rpc_url: str) -> ChainActivity:
        try:
            x = self._post(rpc_url, {"jsonrpc":"2.0","id":1,"method":"getSlot","params":[]})
            if "result" not in x:
                return ChainActivity("solana", 0, time.time(), "Solana JSON-RPC", False, str(x.get("error", "missing result")))
            return ChainActivity("solana", int(x["result"]), time.time(), "Solana JSON-RPC", True, "latest slot")
        except Exception as e:
            return ChainActivity("solana", 0, time.time(), "Solana JSON-RPC", False, str(e))
