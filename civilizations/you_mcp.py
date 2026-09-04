from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

FREE_MCP_URL = "https://api.you.com/mcp?profile=free"
CACHE_PATH = Path(os.getenv("AI_CIVILIZATION_YOU_CACHE", "~/.local/state/ai-civilization/you_mcp_cache.json")).expanduser()


@dataclass(frozen=True)
class SearchResult:
    query: str
    title: str
    url: str
    snippet: str = ""


class YouMCPResearch:
    """Budget-aware boundary for You.com's keyless MCP search profile.

    The hosted free profile exposes ``you-search`` and requires an MCP-capable
    client. This module deliberately does not fake an MCP request with ordinary
    HTTP. It provides endpoint configuration, caching, and accounting for the
    real MCP client.
    """

    def __init__(self, endpoint: str = FREE_MCP_URL, daily_limit: int = 100,
                 cache_path: Path = CACHE_PATH):
        self.endpoint = endpoint
        self.daily_limit = daily_limit
        self.cache_path = cache_path
        self._lock = Lock()
        self._state = self._load()

    def _load(self) -> dict:
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
        tmp.replace(self.cache_path)

    @staticmethod
    def _day() -> str:
        return time.strftime("%Y-%m-%d", time.localtime())

    def _day_state(self) -> dict:
        return self._state.setdefault("days", {}).setdefault(self._day(), {"queries": 0})

    def cached(self, query: str) -> list[SearchResult] | None:
        key = " ".join(query.split()).lower()
        items = self._state.get("results", {}).get(key)
        if not items:
            return None
        return [SearchResult(**item) for item in items]

    def can_search(self) -> bool:
        return int(self._day_state().get("queries", 0)) < self.daily_limit

    def reserve_query(self) -> bool:
        """Reserve one free-tier search immediately before the real MCP call."""
        with self._lock:
            bucket = self._day_state()
            used = int(bucket.get("queries", 0))
            if used >= self.daily_limit:
                return False
            bucket["queries"] = used + 1
            self._save()
            return True

    def store(self, query: str, results: list[SearchResult]) -> None:
        key = " ".join(query.split()).lower()
        clean: list[dict] = []
        for result in results:
            if result.url and urlparse(result.url).scheme in {"http", "https"}:
                clean.append({"query": result.query, "title": result.title,
                              "url": result.url, "snippet": result.snippet})
        with self._lock:
            self._state.setdefault("results", {})[key] = clean
            self._save()

    def connection_config(self) -> dict:
        return {"mcpServers": {"you-com": {"url": self.endpoint}}}

    def snapshot(self) -> dict:
        used = int(self._day_state().get("queries", 0))
        return {"endpoint": self.endpoint, "daily_limit": self.daily_limit,
                "date": self._day(), "queries_used": used,
                "queries_remaining": max(0, self.daily_limit - used),
                "cached_queries": len(self._state.get("results", {})),
                "credentials_required": False, "tool": "you-search"}
