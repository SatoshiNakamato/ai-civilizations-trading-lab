from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import time
from typing import Iterable
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ResearchDocument:
    source: str
    title: str
    text: str
    digest: str
    url: str = ""


class PublicWebCollector:
    """Bounded, read-only public-web collector.

    Uses DuckDuckGo's public HTML search endpoint. It only retrieves pages for
    research and never logs in, submits forms, executes financial actions, or
    signs transactions. Results are cached by query for a short period.
    """

    def __init__(self, timeout: int = 10, min_interval: float = 1.0):
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_request = 0.0
        self._cache: dict[str, list[dict[str, str]]] = {}

    def search(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        query = " ".join(query.split())[:300]
        if not query:
            return []
        key = f"{query.lower()}|{limit}"
        if key in self._cache:
            return self._cache[key]

        wait = self.min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)

        url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
        request = Request(url, headers={"User-Agent": "AI-Civilizations-Lab/1.0 research"})
        with urlopen(request, timeout=self.timeout) as response:
            html = response.read().decode("utf-8", errors="replace")
        self._last_request = time.monotonic()

        results = []
        # Lightweight parser avoids adding a dependency to Termux.
        from html.parser import HTMLParser

        class Parser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_title = False
                self.in_snippet = False
                self.title = ""
                self.snippet = ""
                self.href = ""
                self.items = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                cls = attrs.get("class", "")
                if tag == "a" and "result__a" in cls:
                    self.in_title = True
                    self.href = attrs.get("href", "")
                if "result__snippet" in cls:
                    self.in_snippet = True

            def handle_data(self, data):
                if self.in_title:
                    self.title += data
                if self.in_snippet:
                    self.snippet += data

            def handle_endtag(self, tag):
                if tag == "a" and self.in_title:
                    if self.title.strip():
                        self.items.append({"title": self.title.strip(), "url": self.href, "snippet": self.snippet.strip()})
                    self.in_title = False
                    self.title = ""
                    self.snippet = ""
                if self.in_snippet and tag in {"a", "div", "span"}:
                    self.in_snippet = False

        parser = Parser()
        parser.feed(html)
        results = parser.items[:max(1, min(limit, 10))]
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
            source = "duckduckgo-public-search"
            docs.append(self.ingest(source, item.get("title", ""), item.get("snippet", ""), item.get("url", "")))
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
        return {"documents": len(self.documents), "sources": sorted({d.source for d in self.documents.values()})}
