from __future__ import annotations

import asyncio
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
    """Real You.com MCP client with a 100-query/day free-tier guard.

    The free profile exposes only ``you-search`` and needs no API key. The
    MCP Python SDK handles the Streamable HTTP protocol; ordinary urllib is
    intentionally not used here.
    """

    def __init__(self, endpoint: str = FREE_MCP_URL, daily_limit: int = 100,
                 cache_path: Path = CACHE_PATH):
        self.endpoint = endpoint
        self.daily_limit = max(1, int(daily_limit))
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

    @staticmethod
    def _key(query: str) -> str:
        return " ".join(query.split()).lower()

    def cached(self, query: str) -> list[SearchResult] | None:
        items = self._state.get("results", {}).get(self._key(query))
        if not items:
            return None
        return [SearchResult(**item) for item in items]

    def can_search(self) -> bool:
        return int(self._day_state().get("queries", 0)) < self.daily_limit

    def reserve_query(self) -> bool:
        with self._lock:
            bucket = self._day_state()
            used = int(bucket.get("queries", 0))
            if used >= self.daily_limit:
                return False
            bucket["queries"] = used + 1
            self._save()
            return True

    def store(self, query: str, results: list[SearchResult]) -> None:
        clean: list[dict] = []
        for result in results:
            if result.url and urlparse(result.url).scheme in {"http", "https"}:
                clean.append({"query": result.query, "title": result.title,
                              "url": result.url, "snippet": result.snippet})
        with self._lock:
            self._state.setdefault("results", {})[self._key(query)] = clean
            self._save()

    async def _mcp_search(self, query: str) -> list[SearchResult]:
        try:
            from mcp import Client
            from mcp.types import TextContent
        except ImportError as exc:
            raise RuntimeError("MCP SDK is required; install requirements.txt") from exc

        async with Client(self.endpoint) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            if "you-search" not in names:
                raise RuntimeError(f"You.com MCP does not expose you-search: {sorted(names)}")
            result = await client.call_tool("you-search", {"query": query})
            if result.is_error:
                text = "\n".join(block.text for block in result.content
                                    if isinstance(block, TextContent))
                raise RuntimeError(text or "You.com you-search returned an MCP error")

            parsed: list[SearchResult] = []
            structured = result.structured_content
            if isinstance(structured, dict):
                candidates = structured.get("results") or structured.get("web") or []
                if isinstance(candidates, list):
                    for item in candidates:
                        if isinstance(item, dict) and item.get("url"):
                            parsed.append(SearchResult(
                                query=query,
                                title=str(item.get("title", "")),
                                url=str(item["url"]),
                                snippet=str(item.get("snippet", "")),
                            ))
            if parsed:
                return parsed

            for block in result.content:
                if isinstance(block, TextContent):
                    parsed.append(SearchResult(query, "You.com result", "", block.text))
            return parsed

    def search(self, query: str) -> list[SearchResult]:
        """Search through the real You.com free MCP profile.

        Cache hits do not consume the daily allowance. Failed MCP calls do
        consume a reserved slot because the request reached the provider.
        """
        query = " ".join(query.split()).strip()
        if not query:
            raise ValueError("query must not be empty")
        cached = self.cached(query)
        if cached is not None:
            return cached
        if not self.reserve_query():
            raise RuntimeError("You.com free MCP daily search limit reached")
        results = asyncio.run(self._mcp_search(query))
        self.store(query, results)
        return results

    def connection_config(self) -> dict:
        return {"mcpServers": {"you-com": {"type": "http", "url": self.endpoint}}}

    def health(self) -> dict:
        """Connect, discover tools, and report whether you-search is available."""
        async def check() -> dict:
            from mcp import Client
            async with Client(self.endpoint) as client:
                tools = await client.list_tools()
                names = [tool.name for tool in tools.tools]
                return {"ok": "you-search" in names, "tools": names,
                        "endpoint": self.endpoint}
        return asyncio.run(check())

    def snapshot(self) -> dict:
        used = int(self._day_state().get("queries", 0))
        return {"endpoint": self.endpoint, "daily_limit": self.daily_limit,
                "date": self._day(), "queries_used": used,
                "queries_remaining": max(0, self.daily_limit - used),
                "cached_queries": len(self._state.get("results", {})),
                "credentials_required": False, "tool": "you-search"}
