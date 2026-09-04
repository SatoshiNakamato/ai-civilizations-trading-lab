class StrategyEvolution:
    def __init__(self,min_samples=10): self.min_samples=min_samples; self.history={}; self.active={}
    def record(self,name,pnl):
        h=self.history.setdefault(name,[]); h.append(pnl)
        self.active.setdefault(name,True)
    def evaluate(self):
        out=[]
        for name,vals in self.history.items():
            if len(vals)<self.min_samples: continue
            total=sum(vals); peak=0; equity=0; dd=0
            for v in vals: equity+=v; peak=max(peak,equity); dd=max(dd,peak-equity)
            score=total/(1+dd)
            out.append({'strategy':name,'samples':len(vals),'pnl':total,'drawdown':dd,'score':score,'active':self.active[name]})
        return sorted(out,key=lambda x:x['score'],reverse=True)
    def evolve(self):
        for row in self.evaluate(): self.active[row['strategy']]=row['score']>=0
        return self.evaluate()
