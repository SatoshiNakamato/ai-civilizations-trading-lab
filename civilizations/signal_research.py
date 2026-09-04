from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class PublicSignal:
    kind: str
    title: str
    text: str
    url: str = ""
    score: float = 0.0
    source: str = "public"


class PublicSignalResearch:
    """Keyless public signal collector for meme/news/social discovery.

    X is treated as an optional public-signal input: the collector accepts a
    configured public RSS/search endpoint instead of storing X credentials.
    News and meme feeds are also optional and fail closed. No private account,
    posting, trading, or wallet capability is included.
    """

    DEFAULT_NEWS = (
        "https://news.google.com/rss/search?q=crypto+meme+token&hl=en-US&gl=US&ceid=US:en",
    )
    DEFAULT_MEMES = (
        "https://www.reddit.com/r/memecoin/new/.rss?limit=25",
        "https://www.reddit.com/r/cryptomemes/new/.rss?limit=25",
    )

    def __init__(self):
        self.signals: list[PublicSignal] = []

    def fetch(self, timeout: int = 8) -> list[PublicSignal]:
        urls = self._urls("CIVILIZATION_NEWS_FEEDS", self.DEFAULT_NEWS)
        urls += self._urls("CIVILIZATION_MEME_FEEDS", self.DEFAULT_MEMES)
        # Optional public X-compatible RSS/search bridge supplied by the host.
        urls += self._urls("CIVILIZATION_X_FEEDS", ())
        out: list[PublicSignal] = []
        for url in urls:
            out.extend(self._fetch_rss(url, timeout))
        self.signals = self._rank(out)[:40]
        return self.signals

    @staticmethod
    def _urls(env_name: str, defaults: tuple[str, ...]) -> list[str]:
        raw = os.getenv(env_name, "").strip()
        return [x.strip() for x in raw.split(",") if x.strip()] or list(defaults)

    def _fetch_rss(self, url: str, timeout: int) -> list[PublicSignal]:
        req = urllib.request.Request(url, headers={"Accept": "application/rss+xml, application/xml, text/xml", "User-Agent": "ai-civilizations-trading-lab/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                root = ET.fromstring(response.read())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ET.ParseError):
            return []
        items = []
        for node in root.findall(".//item")[:25]:
            title = self._text(node.find("title"))
            desc = self._text(node.find("description"))
            link = self._text(node.find("link"))
            text = re.sub(r"<[^>]+>", " ", f"{title} {desc}")
            if not title:
                continue
            lower = text.lower()
            meme = any(x in lower for x in ("meme", "memecoin", "doge", "pepe", "cat", "frog", "viral"))
            kind = "meme" if meme else "news"
            score = 0.45 + min(0.35, sum(lower.count(k) for k in ("meme", "viral", "token", "coin", "listing")) * 0.04)
            items.append(PublicSignal(kind, title[:180], text[:500], link[:500], min(0.95, score), urllib.parse.urlparse(url).netloc or "public"))
        return items

    @staticmethod
    def _text(node) -> str:
        return "" if node is None else " ".join("".join(node.itertext()).split())

    @staticmethod
    def _rank(items: list[PublicSignal]) -> list[PublicSignal]:
        seen = set(); unique = []
        for item in sorted(items, key=lambda x: x.score, reverse=True):
            key = re.sub(r"\W+", " ", item.title.lower()).strip()
            if key and key not in seen:
                seen.add(key); unique.append(item)
        return unique

    def snapshot(self):
        return {"signals": [asdict(x) for x in self.signals], "updated_at": time.time()}
