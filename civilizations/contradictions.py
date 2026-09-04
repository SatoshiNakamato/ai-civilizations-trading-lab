from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Contradiction:
    topic: str
    left: str
    right: str
    severity: float

class ContradictionDetector:
    """Flags simple conflicting findings for skeptic review."""
    def __init__(self): self.items: list[Contradiction] = []
    def compare(self, topic: str, findings: list[str]):
        out=[]
        for i,a in enumerate(findings):
            for b in findings[i+1:]:
                al, bl = a.lower(), b.lower()
                neg_a = any(x in al for x in (" no "," not "," unlikely","decline"))
                neg_b = any(x in bl for x in (" no "," not "," unlikely","decline"))
                pos_a = any(x in al for x in (" yes "," likely","rise","increase"))
                pos_b = any(x in bl for x in (" yes "," likely","rise","increase"))
                if (neg_a and pos_b) or (pos_a and neg_b):
                    c=Contradiction(topic,a,b,0.7); self.items.append(c); out.append(c)
        return out
    def snapshot(self): return {"count":len(self.items),"items":[c.__dict__ for c in self.items[-100:]]}
