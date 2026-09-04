import json
from pathlib import Path

class StateStore:
    def __init__(self,path='data/civilization_state.json'): self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
    def save(self,state):
        tmp=self.path.with_suffix('.tmp'); tmp.write_text(json.dumps(state,indent=2,default=str)); tmp.replace(self.path)
    def load(self,default=None):
        if not self.path.exists(): return default if default is not None else {}
        return json.loads(self.path.read_text())
