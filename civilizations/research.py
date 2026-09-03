from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
import time
from typing import Iterable
from urllib.parse import quote_plus, unquote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ResearchDocument:
    source: str
    title: str
    text: str
    digest: str
    url: str = ""


class PublicWebCollector:
    """Bounded, read-only public-web search collector.

    Uses DuckDuckGo's lightweight public HTML endpoint and a parser tolerant of
    markup changes. It only reads public pages and never logs in, submits forms,
    executes financial actions, or signs transactions.
    """

    def __init__(self, timeout: int = 10, min_interval: float = 1.0):
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_request = 0.0
        self._cache: dict[str, list[dict[str, str]]] = {}

    def _fetch(self, endpoint: str, query: str) -> str:
        wait = self.min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        url = endpoint + quote_plus(query)
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        with urlopen(request, timeout=self.timeout) as response:
            html = response.read().decode("utf-8", errors="replace")
        self._last_request = time.monotonic()
        return html

    @staticmethod
    def _clean(value: str) -> str:
        value = re.sub(r"<[^>]+>", " ", value)
        value = re.sub(r"\s+", " ", value)
        return unquote(value).strip()

    def _parse_results(self, html: str) -> list[dict[str, str]]:
        # DuckDuckGo's normal HTML endpoint.
        pattern = re.compile(
            r'<a[^>]+class=["\'][^"\']*result__a[^"\']*["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            re.I | re.S,
        )
        matches = pattern.findall(html)
        results = []
        for href, title_html in matches:
            title = self._clean(title_html)
            if title:
                results.append({"title": title, "url": href, "snippet": ""})

        if results:
            return results

        # DuckDuckGo Lite fallback, whose markup is simpler and more stable.
        pattern = re.compile(
            r'<a[^>]+class=["\']result-link["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            re.I | re.S,
        )
        for href, title_html in pattern.findall(html):
            title = self._clean(title_html)
            if title:
                results.append({"title": title, "url": href, "snippet": ""})

        return results

    def search(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        query = " ".join(query.split())[:300]
        limit = max(1, min(int(limit), 10))
        if not query:
            return []
        key = f"{query.lower()}|{limit}"
        if key in self._cache:
            return self._cache[key]

        html = self._fetch("https://html.duckduckgo.com/html/?q=", query)
        results = self._parse_results(html)
        if not results:
            html = self._fetch("https://lite.duckduckgo.com/lite/?q=", query)
            results = self._parse_results(html)

        results = results[:limit]
        self._cache[key] = results
        return results


class ResearchDesk:
    """Source-aware research inbox with optional public-web collection."""

    def __init__(self, allowed_sources: Iterable[str] | None = None, web_collector: PublicWebCollector | None = None):
        self.allowed_sources = set(allowed_sources or ())
        self.web_collector = web_collector
        self.documents: dict[str, ResearchDocument] = {}

    def ingest(self, source: str, title: str, text: str, url: str = "") -> ResearchDocument:
        if self.allowed_sources and source not in self.allowed_sources:
            raise ValueError("research source is not allowlisted")
        clean = " ".join(text.split())
        digest = sha256(f"{source}\n{title}\n{clean}".encode()).hexdigest()
        document = ResearchDocument(source, title, clean, digest, url)
        self.documents[digest] = document
        return document

    def web_search_and_ingest(self, query: str, limit: int = 5) -> list[ResearchDocument]:
        if self.web_collector is None:
            return []
        docs = []
        for item in self.web_collector.search(query, limit):
            docs.append(
                self.ingest(
                    "duckduckgo-public-search",
                    item.get("title", ""),
                    item.get("snippet", ""),
                    item.get("url", ""),
                )
            )
        return docs

    def search(self, query: str, limit: int = 5) -> list[ResearchDocument]:
        terms = [t.lower() for t in query.split() if t.strip()]
        if not terms:
            return []
        scored = []
        for document in self.documents.values():
            haystack = f"{document.title} {document.text}".lower()
            score = sum(term in haystack for term in terms)
            if score:
                scored.append((score, document))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [document for _, document in scored[:limit]]

    def snapshot(self) -> dict:
        return {
            "documents": len(self.documents),
            "sources": sorted({d.source for d in self.documents.values()}),
        }
