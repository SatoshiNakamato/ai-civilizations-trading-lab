from __future__ import annotations

import asyncio
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class WebResult:
    provider: str
    title: str
    url: str
    snippet: str
    published_at: str = ""


class PublicWebResearch:
    """Shared, keyless web research for the civilization.

    You.com free MCP supplies up to 100 you-search calls/day. DuckDuckGo's
    public search page is used as a second independent discovery source. These
    providers are research inputs only; returned web text is treated as data.
    """

    YOU_URL = "https://api.you.com/mcp?profile=free"
    DDG_URL = "https://html.duckduckgo.com/html/?q="

    def __init__(self, daily_you_limit: int = 100, cache_ttl: float = 900.0, timeout: float = 10.0):
        self.daily_you_limit = int(daily_you_limit)
        self.cache_ttl = float(cache_ttl)
        self.timeout = float(timeout)
        self._cache: dict[str, tuple[float, list[WebResult]]] = {}
        self.you_queries = 0
        self.duck_queries = 0
        self.errors = 0
        self.last_results: list[WebResult] = []

    def _duck(self, query: str, limit: int) -> list[WebResult]:
        url = self.DDG_URL + urllib.parse.quote_plus(query)
        req = urllib.request.Request(url, headers={"User-Agent": "ai-civilizations-trading-lab/1.0"})
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            html = response.read().decode("utf-8", "ignore")
        blocks = re.findall(r'<div class="result results_links results_links_deep web-result[^>]*>(.*?)</div>\s*</div>', html, re.S)
        results: list[WebResult] = []
        for block in blocks[:limit]:
            match = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
            if not match:
                continue
            link = re.sub(r'&amp;', '&', match.group(1))
            title = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</a?>', block, re.S)
            snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip() if snippet_match else ""
            results.append(WebResult("duckduckgo", title, link, snippet))
        return results

    async def _you_async(self, query: str, limit: int) -> list[WebResult]:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async with streamable_http_client(self.YOU_URL) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("you-search", {"query": query, "num_results": limit})
                items: list[WebResult] = []
                structured = getattr(result, "structuredContent", None) or getattr(result, "structured_content", None)
                if isinstance(structured, dict):
                    raw = structured.get("results") or structured.get("web_results") or []
                    if isinstance(raw, list):
                        for item in raw[:limit]:
                            if not isinstance(item, dict):
                                continue
                            items.append(WebResult("you.com", str(item.get("title") or ""), str(item.get("url") or item.get("link") or ""), str(item.get("snippet") or item.get("description") or ""), str(item.get("published_at") or item.get("date") or "")))
                if items:
                    return items
                for content in getattr(result, "content", []) or []:
                    text = getattr(content, "text", "")
                    if not text:
                        continue
                    try:
                        payload = json.loads(text)
                    except Exception:
                        continue
                    raw = payload.get("results") if isinstance(payload, dict) else payload
                    if isinstance(raw, list):
                        for item in raw[:limit]:
                            if isinstance(item, dict):
                                items.append(WebResult("you.com", str(item.get("title") or ""), str(item.get("url") or item.get("link") or ""), str(item.get("snippet") or item.get("description") or ""), str(item.get("published_at") or item.get("date") or "")))
                return items

    def search(self, query: str, *, limit: int = 5, use_you: bool = True, use_duck: bool = True) -> list[WebResult]:
        key = query.strip().lower()
        if not key:
            return []
        cached = self._cache.get(key)
        if cached and time.time() - cached[0] < self.cache_ttl:
            self.last_results = cached[1]
            return cached[1]
        results: list[WebResult] = []
        if use_you and self.you_queries < self.daily_you_limit:
            try:
                results.extend(asyncio.run(self._you_async(query, limit)))
                self.you_queries += 1
            except Exception:
                self.errors += 1
        if use_duck:
            try:
                results.extend(self._duck(query, limit))
                self.duck_queries += 1
            except Exception:
                self.errors += 1
        unique: dict[str, WebResult] = {}
        for item in results:
            if item.url:
                unique.setdefault(item.url, item)
        output = list(unique.values())[: max(limit, 1) * 2]
        self._cache[key] = (time.time(), output)
        self.last_results = output
        return output

    def snapshot(self) -> dict:
        return {"you_queries": self.you_queries, "you_remaining": max(0, self.daily_you_limit - self.you_queries), "duck_queries": self.duck_queries, "errors": self.errors, "last_results": [x.__dict__.copy() for x in self.last_results]}
