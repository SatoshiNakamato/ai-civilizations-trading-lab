from dataclasses import dataclass

@dataclass
class Observation:
    opportunity_id:str; ts:float; state:str; value:float

class ObservationLedger:
    def __init__(self): self.rows=[]
    def record(self,opportunity_id,ts,state,value): self.rows.append(Observation(opportunity_id,ts,state,value))
    def for_opportunity(self,opportunity_id): return [x for x in self.rows if x.opportunity_id==opportunity_id]
