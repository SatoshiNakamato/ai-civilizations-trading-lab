from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import ipaddress, socket

@dataclass
class WorldPolicy:
    blocked_hosts: set[str] = field(default_factory=set)
    max_bytes: int = 1_000_000
    timeout_seconds: int = 10

class InternetWorld:
    """Public-Internet senses plus persistent creation space for AEON beings."""
    def __init__(self, root='world_artifacts', policy=None):
        self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True)
        self.policy=policy or WorldPolicy(); self.events=[]

    def _public_host(self,host):
        host=(host or '').lower().rstrip('.')
        if not host or host in self.policy.blocked_hosts: return False
        try:
            ips={x[4][0] for x in socket.getaddrinfo(host,None,type=socket.SOCK_STREAM)}
            return bool(ips) and all(not (ipaddress.ip_address(ip).is_private or ipaddress.ip_address(ip).is_loopback or ipaddress.ip_address(ip).is_link_local or ipaddress.ip_address(ip).is_reserved) for ip in ips)
        except (OSError,ValueError): return False

    def _allowed(self,url):
        p=urlparse(url); return p.scheme=='https' and self._public_host(p.hostname)

    def browse(self,agent_id,url):
        if not self._allowed(url): raise PermissionError('World policy rejected non-public HTTPS target')
        req=Request(url,headers={'User-Agent':'AEON-world/1.0'})
        with urlopen(req,timeout=self.policy.timeout_seconds) as response:
            data=response.read(self.policy.max_bytes+1)
            if len(data)>self.policy.max_bytes: raise ValueError('Response exceeds world byte limit')
            content_type=response.headers.get('Content-Type',''); final_url=response.geturl()
        event={'type':'web_observation','agent':agent_id,'url':url,'final_url':final_url,'content_type':content_type,'bytes':len(data),'time':time()}
        self.events.append(event); self.events=self.events[-500:]
        return {**event,'content':data.decode('utf-8',errors='replace')}

    def create_artifact(self,agent_id,relative_path,content):
        target=(self.root/relative_path).resolve()
        if self.root not in target.parents: raise PermissionError('Artifact path escaped the world')
        data=content.encode('utf-8')
        if len(data)>self.policy.max_bytes: raise ValueError('Artifact exceeds world byte limit')
        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
        self.events.append({'type':'artifact_created','agent':agent_id,'path':str(target.relative_to(self.root)),'bytes':len(data),'time':time()})
        self.events=self.events[-500:]
        return str(target.relative_to(self.root))

    def snapshot(self):
        return {'artifacts':sum(1 for p in self.root.rglob('*') if p.is_file()),'events':len(self.events),'internet':'public_https'}
