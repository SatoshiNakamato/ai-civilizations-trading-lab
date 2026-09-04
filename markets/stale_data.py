from dataclasses import dataclass
import time

@dataclass
class QuotePoint:
    venue:str; bid:float; ask:float; ts:float
    def age(self,now=None): return (now or time.time())-self.ts

class StaleDataGuard:
    def __init__(self,max_age_seconds=5): self.max_age_seconds=max_age_seconds
    def fresh(self,q,now=None): return q.age(now) <= self.max_age_seconds
    def filter(self,quotes,now=None): return [q for q in quotes if self.fresh(q,now)]
