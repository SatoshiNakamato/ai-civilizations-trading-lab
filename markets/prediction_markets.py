from dataclasses import dataclass

@dataclass
class PredictionMarketSignal:
    market:str; implied_probability:float; estimated_probability:float; confidence:float
    @property
    def edge(self): return self.estimated_probability-self.implied_probability

class PredictionMarketBook:
    def __init__(self): self.signals=[]
    def add(self,signal): self.signals.append(signal)
    def best(self,n=3): return sorted(self.signals,key=lambda s:abs(s.edge)*s.confidence,reverse=True)[:n]
