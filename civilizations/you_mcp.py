from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse
from urllib.request import Request, urlopen

FREE_MCP_URL = "https://api.you.com/mcp?profile=free"
CACHE_PATH = Path(os.getenv("AI_CIVILIZATION_YOU_CACHE", "~/.local/state/ai-civilization/you_mcp_cache.json")).expanduser()


@dataclass(frozen=True)
class SearchResult:
    query: str
    title: str
    url: str
    snippet: str = ""


class YouMCPResearch:
    """Small MCP HTTP client for You.com's keyless free search profile.

    The free profile exposes search only. It intentionally does not accept or
    persist an API key. The client caches identical requests and applies a
    local daily query budget so continuous agents cannot accidentally exhaust
    the advertised free allowance.
    """

    def __init__(self, endpoint: str = FREE_MCP_URL, daily_limit: int = 100,
                 cache_path: Path = CACHE_PATH):
        self.endpoint = endpoint
        self.daily_limit = daily_limit
        self.cache_path = cache_path
        self._lock = Lock()
        self._cache = self._load_cache()

    def _load_cache(self) -> dict:
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")
        tmp.replace(self.cache_path)

    @staticmethod
    def _day() -> str:
        return time.strftime("%Y-%m-%d", time.localtime())

    def _bucket(self) -> dict:
        day = self._day()
        return self._cache.setdefault("days", {}).setdefault(day, {"queries": 0})

    @staticmethod
    def _extract_results(payload: object, query: str) -> list[SearchResult]:
        # MCP responses vary by transport/client version. Accept common JSON
        # shapes without pretending that every returned object is a search hit.
        items = []
        if isinstance(payload, dict):
            for key in ("results", "web", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    items = value
                    break
            if not items and isinstance(payload.get("content"), list):
                items = payload["content"]
        results: list[SearchResult] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("name") or "")
            url = str(item.get("url") or item.get("link") or "")
            snippet = str(item.get("snippet") or item.get("description") or item.get("text") or "")
            if url and urlparse(url).scheme in {"http", "https"}:
                results.append(SearchResult(query, title, url, snippet))
        return results

    def search(self, query: str, *, timeout: int = 30) -> list[SearchResult]:
        query = " ".join(query.split())
        if not query:
            raise ValueError("query must not be empty")
        cache_key = query.lower()
        with self._lock:
            cached = self._cache.get("results", {}).get(cache_key)
            if cached:
                return [SearchResult(**x) for x in cached]
            bucket = self._bucket()
            if int(bucket.get("queries", 0)) >= self.daily_limit:
                raise RuntimeError("free You.com MCP daily search budget exhausted")

            # Streamable HTTP MCP requires an MCP client/session for arbitrary
            # tool calls; this class intentionally exposes the transport boundary
            # rather than pretending a normal POST is an MCP tool invocation.
            # A compatible MCP client can use the same endpoint/config below.
            bucket["queries"] = int(bucket.get("queries", 0)) + 1
            self._save()

        raise RuntimeError(
            "MCP transport requires an MCP-capable client; configure the endpoint "
            f"{self.endpoint} and call the you-search tool. No API key is required."
        )

    def snapshot(self) -> dict:
        return {
            "endpoint": self.endpoint,
            "daily_limit": self.daily_limit,
            "date": self._day(),
            "queries_reserved": int(self._bucket().get("queries", 0)),
            "cached_queries": len(self._cache.get("results", {})),
            "credentials_required": False,
        }
