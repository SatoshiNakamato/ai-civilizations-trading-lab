class OpportunityRanker:
    def rank(self, opportunities):
        return sorted(opportunities,key=self.score,reverse=True)
    def score(self,o):
        edge=max(0.0,getattr(o,'net_edge',0.0)); conf=getattr(o,'confidence',0.0); liq=getattr(o,'liquidity',0.0)
        return edge*conf*min(1.0,liq)
