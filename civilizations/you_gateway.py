from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

from .provider_adapters import ProviderResponse, YouResearchAdapter
from .provider_manager import ProviderManager

CACHE_PATH = Path(__import__('os').getenv('AI_CIVILIZATION_YOU_CACHE', '~/.local/state/ai-civilization/you_cache.json')).expanduser()

@dataclass(frozen=True)
class ResearchRequest:
    agent_id: str
    question: str
    effort: str = 'lite'
    freshness: str | None = None
    include_domains: tuple[str, ...] = ()

@dataclass
class GatewayStats:
    requests: int = 0
    cache_hits: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0

class YouIntelligenceGateway:
    """Budget-aware You.com gateway for selective deep research.

    Only A002 is authorized by default. Results are cached locally so repeated
    civilization questions do not consume credits unnecessarily. Credentials
    remain inside ProviderManager and never enter cache records.
    """
    def __init__(self, manager: ProviderManager | None = None, cache_path: Path = CACHE_PATH):
        self.manager = manager or ProviderManager()
        self.adapter = YouResearchAdapter(self.manager)
        self.cache_path = cache_path
        self.stats = GatewayStats()
        self._lock = Lock()
        self._cache = self._load_cache()

    def _load_cache(self) -> dict[str, Any]:
        try:
            data = json.loads(self.cache_path.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self._cache, ensure_ascii=False), encoding='utf-8')
        tmp.replace(self.cache_path)

    @staticmethod
    def _key(req: ResearchRequest) -> str:
        material = json.dumps({
            'question': req.question.strip(),
            'effort': req.effort,
            'freshness': req.freshness,
            'include_domains': req.include_domains,
        }, sort_keys=True)
        return hashlib.sha256(material.encode()).hexdigest()

    def research(self, req: ResearchRequest, cache_ttl_seconds: int = 3600) -> ProviderResponse:
        self.stats.requests += 1
        if req.agent_id != 'A002':
            self.stats.skipped += 1
            return ProviderResponse('you', False, error='agent_not_assigned')
        if req.effort not in {'lite', 'standard', 'deep', 'exhaustive'}:
            self.stats.skipped += 1
            return ProviderResponse('you', False, error='invalid_research_effort')

        key = self._key(req)
        now = time.time()
        with self._lock:
            cached = self._cache.get(key)
            if cached and now - float(cached.get('created_at', 0)) <= cache_ttl_seconds:
                self.stats.cache_hits += 1
                return ProviderResponse('you', True, str(cached.get('content', '')), list(cached.get('sources', [])))

        # Reserve a provider call only after the cache check.
        auth = self.manager.authorize(req.agent_id, 'web_research')
        if not auth.get('allowed'):
            self.stats.skipped += 1
            return ProviderResponse('you', False, error=auth.get('reason', 'not_authorized'))

        try:
            data = self.adapter._research_without_authorize(req.question, req.effort, req.freshness, req.include_domains)
            response = data
        except Exception as exc:
            self.stats.failed += 1
            return ProviderResponse('you', False, error=f'{type(exc).__name__}: {exc}')

        self.stats.successful += 1
        with self._lock:
            self._cache[key] = {
                'created_at': now,
                'content': response.content,
                'sources': response.sources,
            }
            self._save_cache()
        return response

    def snapshot(self) -> dict[str, Any]:
        return {
            'provider': 'you',
            'assigned_agent': 'A002',
            'stats': self.stats.__dict__.copy(),
            'cache_entries': len(self._cache),
            'manager': self.manager.snapshot(),
        }

# Keep the low-level request isolated so the gateway can reserve budget before
# the network call and can add caching without changing the public adapter API.
def _research_without_authorize(self: YouResearchAdapter, question: str, effort: str,
                                freshness: str | None, include_domains: tuple[str, ...]) -> ProviderResponse:
    payload: dict[str, Any] = {'input': question[:40000], 'research_effort': effort}
    source_control: dict[str, Any] = {}
    if freshness:
        source_control['freshness'] = freshness
    if include_domains:
        source_control['include_domains'] = list(include_domains)
    if source_control:
        payload['source_control'] = source_control
    request = urllib.request.Request(
        self.endpoint,
        data=json.dumps(payload).encode(),
        headers={'X-API-Key': self.manager.credential_for('you') or '', 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode('utf-8'))
    output = data.get('output', {}) or {}
    sources = [
        {'title': str(s.get('title', '')), 'url': str(s.get('url', ''))}
        for s in (output.get('sources', []) or []) if isinstance(s, dict)
    ]
    return ProviderResponse('you', True, str(output.get('content', '')), sources)

YouResearchAdapter._research_without_authorize = _research_without_authorize
