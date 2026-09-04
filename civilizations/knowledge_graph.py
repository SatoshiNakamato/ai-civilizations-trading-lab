from __future__ import annotations
from collections import defaultdict
class KnowledgeGraph:
    def __init__(self): self.nodes={}; self.edges=defaultdict(set)
    def add(self,node_id,kind,data=None): self.nodes[node_id]={'kind':kind,'data':data or {}}
    def link(self,a,b,relation='related'):
        self.edges[a].add((relation,b)); self.edges[b].add((relation,a))
    def related(self,node_id): return list(self.edges.get(node_id,()))
    def snapshot(self): return {'nodes':len(self.nodes),'edges':sum(len(v) for v in self.edges.values())//2}
