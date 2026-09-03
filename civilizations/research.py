from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
import time
from typing import Iterable
from urllib.parse import quote_plus, unquote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class ResearchDocument:
    source: str
    title: str
    text: str
    digest: str
    url: str = ""


class PublicWebCollector:
    """Bounded, read-only public-web research collector.

    Primary source is Google News RSS, with DuckDuckGo HTML as a fallback.
    RSS is used because it is lightweight and works well in constrained
    environments such as Termux. The collector only reads public information.
    """

    def __init__(self, timeout: int = 10, min_interval: float = 1.0):
        self.timeout = timeout
        self.min_interval = min_interval
        self._last_request = 0.0
        self._cache: dict[str, list[dict[str, str]]] = {}

    def _fetch(self, url: str) -> str:
        wait = self.min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        request = Request(
            url,
            headers={
                "User-Agent": "AI-Civilizations-Lab/1.0 (research; read-only)",
                "Accept": "application/rss+xml, application/xml, text/html;q=0.9, */*;q=0.8",
            },
        )
        with urlopen(request, timeout=self.timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
        self._last_request = time.monotonic()
        return body

    @staticmethod
    def _clean(value: str) -> str:
        value = re.sub(r"<[^>]+>", " ", value)
        value = re.sub(r"\s+", " ", value)
        return unquote(value).strip()

    def _google_news(self, query: str, limit: int) -> list[dict[str, str]]:
        url = "https://news.google.com/rss/search?q=" + quote_plus(query) + "&hl=en-US&gl=US&ceid=US:en"
        xml = self._fetch(url)
        root = ET.fromstring(xml)
        results = []
        for item in root.findall(".//item"):
            title = self._clean(item.findtext("title", ""))
            link = self._clean(item.findtext("link", ""))
            description = self._clean(item.findtext("description", ""))
            pubdate = self._clean(item.findtext("pubDate", ""))
            source = item.findtext("source", "") or "Google News"
            if title:
                results.append({
                    "title": title,
                    "url": link,
                    "snippet": description,
                    "published": pubdate,
                    "source": self._clean(source),
                })
            if len(results) >= limit:
                break
        return results

    def _duckduckgo(self, query: str, limit: int) -> list[dict[str, str]]:
        url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
        html = self._fetch(url)
        pattern = re.compile(
            r'<a[^>]+class=["\'][^"\']*result__a[^"\']*["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            re.I | re.S,
        )
        results = []
        for href, title_html in pattern.findall(html):
            title = self._clean(title_html)
            if title:
                results.append({"title": title, "url": href, "snippet": "", "source": "DuckDuckGo"})
        return results[:limit]

    def search(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        query = " ".join(query.split())[:300]
        limit = max(1, min(int(limit), 10))
        if not query:
            return []
        key = f"{query.lower()}|{limit}"
        if key in self._cache:
            return self._cache[key]

        results: list[dict[str, str]] = []
        try:
            results = self._google_news(query, limit)
        except Exception:
            pass
        if not results:
            try:
                results = self._duckduckgo(query, limit)
            except Exception:
                results = []

        self._cache[key] = results[:limit]
        return self._cache[key]


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
            source = item.get("source", "public-web")
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
        return {
            "documents": len(self.documents),
            "sources": sorted({d.source for d in self.documents.values()}),
        }
