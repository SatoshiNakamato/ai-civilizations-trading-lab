from dataclasses import dataclass

@dataclass
class CivilizationState:
    generation:int=0; cycles:int=0; status:str='running'

class CivilizationOrchestrator:
    def __init__(self,components=None): self.components=components or {}; self.state=CivilizationState()
    def cycle(self):
        self.state.cycles+=1
        result={}
        for name,component in self.components.items():
            if hasattr(component,'cycle'): result[name]=component.cycle()
        return result
    def snapshot(self): return {'generation':self.state.generation,'cycles':self.state.cycles,'status':self.state.status}
