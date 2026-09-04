from dataclasses import dataclass

@dataclass
class ExecutionModel:
    fee_rate: float=0.001
    slippage_bps: float=5.0
    latency_seconds: float=0.25
    fill_ratio: float=1.0
    liquidity_multiplier: float=1.0
    def cost(self, notional): return notional*self.fee_rate + notional*self.slippage_bps/10000
    def effective_fill(self, quantity, available): return max(0.0,min(quantity,available*self.liquidity_multiplier))*self.fill_ratio
