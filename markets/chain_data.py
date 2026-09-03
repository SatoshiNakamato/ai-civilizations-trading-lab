from __future__ import annotations

import json
import time
import urllib.request


class PublicChainData:
    """Minimal read-only chain connectivity.

    Explorer APIs can require keys; direct public RPC endpoints are used here
    for basic connectivity checks. No private keys or transaction submission.
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.evm_rpcs = {
            "ethereum": "https://cloudflare-eth.com",
            "base": "https://mainnet.base.org",
        }
        self.solana_rpc = "https://api.mainnet-beta.solana.com"

    def _post(self, url: str, payload: dict):
        body = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "ai-civilizations-trading-lab/1.0"})
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode())

    def evm_block(self, chain: str) -> int:
        result = self._post(self.evm_rpcs[chain], {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []})
        return int(result["result"], 16)

    def solana_slot(self) -> int:
        result = self._post(self.solana_rpc, {"jsonrpc": "2.0", "id": 1, "method": "getSlot", "params": []})
        return int(result["result"])

    def health(self) -> dict:
        out = {"timestamp": time.time(), "evm": {}, "solana": None}
        for chain in self.evm_rpcs:
            try:
                out["evm"][chain] = {"ok": True, "block": self.evm_block(chain)}
            except Exception as exc:
                out["evm"][chain] = {"ok": False, "error": str(exc)}
        try:
            out["solana"] = {"ok": True, "slot": self.solana_slot()}
        except Exception as exc:
            out["solana"] = {"ok": False, "error": str(exc)}
        return out
