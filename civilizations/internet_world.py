from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass
class WorldPolicy:
    """Capability boundary for the digital world."""
    allowed_domains: set[str] = field(default_factory=lambda: {
        "github.com", "raw.githubusercontent.com", "api.github.com"
    })
    max_bytes: int = 512_000
    timeout_seconds: int = 8


class InternetWorld:
    """Read-only web access plus inert artifact creation inside the world.

    Agents may observe approved public HTTPS sources and create files in the
    world artifact directory. Generated programs are deliberately not executed
    automatically; execution remains a separate, explicit capability.
    """

    def __init__(self, root: str = "world_artifacts", policy: WorldPolicy | None = None):
        self.root = Path(root).resolve(); self.root.mkdir(parents=True, exist_ok=True)
        self.policy = policy or WorldPolicy(); self.events: list[dict] = []

    def _allowed(self, url: str) -> bool:
        parsed = urlparse(url); host = (parsed.hostname or "").lower()
        return parsed.scheme == "https" and (host in self.policy.allowed_domains or any(host.endswith("." + d) for d in self.policy.allowed_domains))

    def browse(self, agent_id: str, url: str) -> dict:
        if not self._allowed(url):
            raise PermissionError("World policy rejected this URL")
        req = Request(url, headers={"User-Agent": "AEON-world/1.0"})
        with urlopen(req, timeout=self.policy.timeout_seconds) as response:
            data = response.read(self.policy.max_bytes + 1)
            if len(data) > self.policy.max_bytes: raise ValueError("Response exceeds world byte limit")
            content_type = response.headers.get("Content-Type", "")
        event = {"type":"web_observation","agent":agent_id,"url":url,"content_type":content_type,"bytes":len(data),"time":time()}
        self.events.append(event); self.events = self.events[-200:]
        return {**event, "content": data.decode("utf-8", errors="replace")}

    def create_artifact(self, agent_id: str, relative_path: str, content: str) -> str:
        target = (self.root / relative_path).resolve()
        if self.root not in target.parents: raise PermissionError("Artifact path escaped the world")
        data = content.encode("utf-8")
        if len(data) > self.policy.max_bytes: raise ValueError("Artifact exceeds world byte limit")
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        self.events.append({"type":"artifact_created","agent":agent_id,"path":str(target.relative_to(self.root)),"bytes":len(data),"time":time()})
        self.events = self.events[-200:]
        return str(target.relative_to(self.root))

    def snapshot(self) -> dict:
        return {"artifacts":sum(1 for p in self.root.rglob("*") if p.is_file()),"events":len(self.events),"allowed_domains":sorted(self.policy.allowed_domains)}
