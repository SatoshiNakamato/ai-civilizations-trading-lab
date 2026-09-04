class Portfolio:
    def __init__(self): self.positions={}; self.realized_pnl=0.0
    def open(self,key,notional): self.positions[key]=self.positions.get(key,0.0)+notional
    def close(self,key,pnl):
        self.positions.pop(key,None); self.realized_pnl+=pnl
    @property
    def exposure(self): return sum(abs(x) for x in self.positions.values())
    def snapshot(self): return {'positions':dict(self.positions),'exposure':self.exposure,'realized_pnl':self.realized_pnl}
