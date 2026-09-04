from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
import urllib.error
import urllib.request


RPC_ENV = {
    "base": "BANKR_RPC_URL_BASE",
    "robinhood": "BANKR_RPC_URL_ROBINHOOD",
}


@dataclass
class VerificationResult:
    status: str
    chain: str
    token_address: str = ""
    tx_hash: str = ""
    block_number: str = ""
    confirmations: int = 0
    error: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


class DeploymentVerifier:
    """Verify that a Bankr launch was actually broadcast and exists on-chain.

    A token address returned by a partial/simulation response is not treated as
    deployed. Verification requires a transaction hash, a successful receipt,
    and bytecode at the reported token address.
    """

    def __init__(self, rpc_urls: dict[str, str] | None = None, timeout: int = 15):
        self.rpc_urls = dict(rpc_urls or {})
        for chain, env_name in RPC_ENV.items():
            value = os.getenv(env_name, "").strip()
            if value:
                self.rpc_urls.setdefault(chain, value)
        self.timeout = timeout

    def verify(self, chain: str, token_address: str, tx_hash: str) -> VerificationResult:
        chain = chain.lower()
        token_address = str(token_address or "")
        tx_hash = str(tx_hash or "")
        if not tx_hash:
            return VerificationResult("partial_simulation", chain, token_address, error="no transaction hash; launch was not proven broadcast")
        rpc_url = self.rpc_urls.get(chain, "")
        if not rpc_url:
            return VerificationResult("pending", chain, token_address, tx_hash, error=f"no RPC configured for {chain}; set {RPC_ENV.get(chain, 'BANKR_RPC_URL_' + chain.upper())}")
        try:
            receipt = self._rpc(rpc_url, "eth_getTransactionReceipt", [tx_hash])
            if receipt is None:
                return VerificationResult("pending", chain, token_address, tx_hash, error="transaction receipt is not available yet")
            if receipt.get("status") == "0x0":
                return VerificationResult("failed", chain, token_address, tx_hash, block_number=str(receipt.get("blockNumber", "")), error="transaction receipt reports failure")
            if not token_address:
                return VerificationResult("pending", chain, token_address, tx_hash, block_number=str(receipt.get("blockNumber", "")), error="receipt succeeded but token address is missing")
            code = self._rpc(rpc_url, "eth_getCode", [token_address, "latest"])
            if not code or code == "0x":
                return VerificationResult("pending", chain, token_address, tx_hash, block_number=str(receipt.get("blockNumber", "")), error="transaction succeeded but token contract bytecode is not visible yet")
            return VerificationResult("verified", chain, token_address, tx_hash, block_number=str(receipt.get("blockNumber", "")), confirmations=1)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
            return VerificationResult("error", chain, token_address, tx_hash, error=f"{type(exc).__name__}: {exc}")

    def _rpc(self, url: str, method: str, params: list) -> dict | str | None:
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            body = json.loads(response.read().decode())
        if body.get("error"):
            raise ValueError(str(body["error"]))
        return body.get("result")

    @staticmethod
    def snapshot(result: VerificationResult) -> dict:
        return result.as_dict()
