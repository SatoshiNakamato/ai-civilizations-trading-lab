class MarketAdapter:
    name='abstract'
    def snapshot(self): raise NotImplementedError

class CompositeMarket:
    def __init__(self,adapters=()): self.adapters=list(adapters)
    def snapshot(self):
        out=[]
        for a in self.adapters:
            try: out.extend(a.snapshot())
            except Exception: continue
        return out
