from __future__ import annotations
import json, time
from pathlib import Path

class AuditLog:
    def __init__(self, path='data/opportunity_lifecycle.jsonl'):
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
    def append(self,event,**payload):
        row={'ts':time.time(),'event':event,**payload}
        with self.path.open('a',encoding='utf-8') as f: f.write(json.dumps(row,separators=(',',':'))+'\n')
        return row
    def read(self):
        if not self.path.exists(): return []
        return [json.loads(x) for x in self.path.read_text().splitlines() if x.strip()]
