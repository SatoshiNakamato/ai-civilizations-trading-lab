from __future__ import annotations
import html
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

@dataclass(frozen=True)
class FallbackResult:
    query: str
    title: str
    url: str
    snippet: str = ""

class DuckDuckGoFallback:
    """Small dependency-free fallback search used only after You.com fails."""
    endpoint = "https://html.duckduckgo.com/html/?q="

    def search(self, query: str, limit: int = 5) -> list[FallbackResult]:
        url = self.endpoint + urllib.parse.quote_plus(query)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research-runtime)"})
        with urllib.request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8", "replace")
        results=[]
        pattern=re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.I|re.S)
        for raw_url, raw_title in pattern.findall(body)[:max(1, int(limit))]:
            title=re.sub(r"<[^>]+>", "", raw_title)
            title=html.unescape(" ".join(title.split()))
            target=html.unescape(raw_url)
            if target.startswith("//duckduckgo.com/l/?"):
                parsed=urllib.parse.parse_qs(urllib.parse.urlparse(target).query)
                target=parsed.get("uddg", [target])[0]
            results.append(FallbackResult(query, title, target, "fallback search result"))
        return results
