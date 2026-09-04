from dataclasses import dataclass

@dataclass
class AlertPolicy:
    min_confidence:float=.9; min_edge:float=.01; min_score:float=.8

class ImportantAlertGate:
    def __init__(self,policy=None): self.policy=policy or AlertPolicy(); self.seen=set()
    def decide(self,o):
        key=getattr(o,'opportunity_id',id(o))
        if key in self.seen: return None
        ok=(getattr(o,'confidence',0)>=self.policy.min_confidence and getattr(o,'net_edge',0)>=self.policy.min_edge and getattr(o,'score',0)>=self.policy.min_score)
        if ok: self.seen.add(key); return 'CRITICAL' if getattr(o,'net_edge',0)>=self.policy.min_edge*2 else 'HIGH'
        return None
