class RiskLimits:
    def __init__(self,max_position=1000.0,max_total=5000.0,max_loss=250.0): self.max_position=max_position; self.max_total=max_total; self.max_loss=max_loss
class RiskGovernor:
    def __init__(self,limits=None): self.limits=limits or RiskLimits(); self.exposure=0.0; self.daily_pnl=0.0; self.halted=False
    def approve(self,amount): return (not self.halted and abs(amount)<=self.limits.max_position and abs(self.exposure+amount)<=self.limits.max_total and self.daily_pnl>-self.limits.max_loss)
    def apply(self,amount):
        if not self.approve(amount): return False
        self.exposure+=amount; return True
    def settle(self,pnl,amount):
        self.exposure-=amount; self.daily_pnl+=pnl
        if self.daily_pnl<=-self.limits.max_loss: self.halted=True
