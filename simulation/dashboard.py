import json
from pathlib import Path

class Dashboard:
    def render(self,snapshot):
        paper=snapshot.get('paper',{})
        return {'status':'ok','cycles':snapshot.get('cycles',0),'realized_pnl':paper.get('realized_pnl',0.0),'open':paper.get('open',0),'top_strategies':snapshot.get('top_strategies',[])}
    def text(self,snapshot): return json.dumps(self.render(snapshot),indent=2,default=str)
