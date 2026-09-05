from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from time import time
from urllib.parse import urlparse, quote_plus
from urllib.request import Request, urlopen
import ipaddress, socket, re

from .evolution_governor import EvolutionGovernor, EvolutionGovernorConfig

@dataclass
class WorldPolicy:
    blocked_hosts: set[str] = field(default_factory=set)
    max_bytes: int = 1_000_000
    timeout_seconds: int = 10

class InternetWorld:
    """Public Internet senses plus governed persistent creation space for AEON beings."""
    def __init__(self, root='world_artifacts', policy=None, evolution_governor=None):
        self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True)
        self.policy=policy or WorldPolicy(); self.events=[]
        evolution_root = self.root.parent / 'data' / 'evolution'
        self.evolution = evolution_governor or EvolutionGovernor(
            EvolutionGovernorConfig(workspace=evolution_root, max_file_bytes=self.policy.max_bytes)
        )

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
        req=Request(url,headers={'User-Agent':'AEON-world/1.1'})
        with urlopen(req,timeout=self.policy.timeout_seconds) as response:
            data=response.read(self.policy.max_bytes+1)
            if len(data)>self.policy.max_bytes: raise ValueError('Response exceeds world byte limit')
            content_type=response.headers.get('Content-Type',''); final_url=response.geturl()
        event={'type':'web_observation','agent':agent_id,'url':url,'final_url':final_url,'content_type':content_type,'bytes':len(data),'time':time()}
        self.events.append(event); self.events=self.events[-300:]
        return {**event,'content':data.decode('utf-8',errors='replace')}

    def search(self,agent_id,query):
        """Search the public web and return compact results for an autonomous research turn."""
        query=' '.join(str(query).split())[:240]
        if not query: return {'query':'','results':[]}
        url='https://html.duckduckgo.com/html/?q='+quote_plus(query)
        page=self.browse(agent_id,url)
        html=page['content']
        results=[]
        for match in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',html,re.I|re.S):
            href=re.sub(r'&amp;','&',match.group(1)); title=re.sub(r'<[^>]+>','',match.group(2)); title=re.sub(r'\s+',' ',title).strip()
            if href.startswith('https://'):
                results.append({'title':title[:300],'url':href[:1000]})
            if len(results)>=5: break
        self.events.append({'type':'web_search','agent':agent_id,'query':query,'results':len(results),'time':time()}); self.events=self.events[-300:]
        return {'query':query,'results':results}

    def create_artifact(self,agent_id,relative_path,content):
        """Create a durable artifact through the evolution governor.

        Existing callers keep their API, while persistence is now subject to
        namespace, path, byte, file-count and audit controls.
        """
        # World artifacts remain a separate inert output surface. The governor
        # stores the same content under agent memory so it survives restarts and
        # can later be promoted to a reviewed repository artifact.
        relative_path = relative_path.replace('\\', '/')
        parts = Path(relative_path).parts
        if not parts or parts[0] != agent_id:
            raise PermissionError('artifact must be owned by its creating agent')
        record = self.evolution.write(agent_id, 'memory', relative_path, content)
        target=(self.root/relative_path).resolve()
        if self.root not in target.parents: raise PermissionError('Artifact path escaped the world')
        data=content.encode('utf-8')
        if len(data)>self.policy.max_bytes: raise ValueError('Artifact exceeds world byte limit')
        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
        self.events.append({'type':'artifact_created','agent':agent_id,'path':str(target.relative_to(self.root)),'bytes':len(data),'time':time(),'evolution_record':record.sha256})
        self.events=self.events[-300:]
        return str(target.relative_to(self.root))

    def snapshot(self):
        return {'artifacts':sum(1 for p in self.root.rglob('*') if p.is_file()),'events':len(self.events),'internet':'public_https','search':'duckduckgo_html','evolution_governor':True}
