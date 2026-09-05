from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
import time
from collections import OrderedDict
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
    """Bounded, read-only public-web research collector."""
    def __init__(self, timeout: int = 10, min_interval: float = 1.0, cache_limit: int = 32):
        self.timeout=timeout; self.min_interval=min_interval; self._last_request=0.0; self.cache_limit=max(4,cache_limit); self._cache=OrderedDict()
    def _fetch(self,url):
        wait=self.min_interval-(time.monotonic()-self._last_request)
        if wait>0: time.sleep(wait)
        request=Request(url,headers={"User-Agent":"AI-Civilizations-Lab/1.0 (research; read-only)","Accept":"application/rss+xml, application/xml, text/html;q=0.9, */*;q=0.8"})
        with urlopen(request,timeout=self.timeout) as response: body=response.read().decode('utf-8',errors='replace')
        self._last_request=time.monotonic(); return body
    @staticmethod
    def _clean(value): return unquote(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',value))).strip()
    def _google_news(self,query,limit):
        root=ET.fromstring(self._fetch('https://news.google.com/rss/search?q='+quote_plus(query)+'&hl=en-US&gl=US&ceid=US:en')); results=[]
        for item in root.findall('.//item'):
            title=self._clean(item.findtext('title','')); link=self._clean(item.findtext('link','')); desc=self._clean(item.findtext('description','')); pub=self._clean(item.findtext('pubDate','')); source=self._clean(item.findtext('source','') or 'Google News')
            if title: results.append({'title':title,'url':link,'snippet':desc[:1000],'published':pub,'source':source})
            if len(results)>=limit: break
        return results
    def _duckduckgo(self,query,limit):
        html=self._fetch('https://html.duckduckgo.com/html/?q='+quote_plus(query)); pattern=re.compile(r'<a[^>]+class=["\'][^"\']*result__a[^"\']*["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',re.I|re.S); results=[]
        for href,title_html in pattern.findall(html):
            title=self._clean(title_html)
            if title: results.append({'title':title,'url':href,'snippet':'','source':'DuckDuckGo'})
        return results[:limit]
    def search(self,query,limit=5):
        query=' '.join(query.split())[:300]; limit=max(1,min(int(limit),10))
        if not query:return []
        key=f'{query.lower()}|{limit}'
        if key in self._cache:
            value=self._cache.pop(key); self._cache[key]=value; return value
        results=[]
        try: results=self._google_news(query,limit)
        except Exception: pass
        if not results:
            try: results=self._duckduckgo(query,limit)
            except Exception: results=[]
        self._cache[key]=results[:limit]
        while len(self._cache)>self.cache_limit:self._cache.popitem(last=False)
        return self._cache[key]

class ResearchDesk:
    """Source-aware research inbox with bounded in-memory document storage."""
    def __init__(self,allowed_sources:Iterable[str]|None=None,web_collector:PublicWebCollector|None=None,document_limit:int=500):
        self.allowed_sources=set(allowed_sources or ()); self.web_collector=web_collector; self.document_limit=max(50,document_limit); self.documents=OrderedDict()
    def ingest(self,source,title,text,url=''):
        if self.allowed_sources and source not in self.allowed_sources: raise ValueError('research source is not allowlisted')
        clean=' '.join(text.split())[:3000]; digest=sha256(f'{source}\n{title}\n{clean}'.encode()).hexdigest(); document=ResearchDocument(source,title[:500],clean,digest,url[:2000]); self.documents.pop(digest,None); self.documents[digest]=document
        while len(self.documents)>self.document_limit:self.documents.popitem(last=False)
        return document
    def web_search_and_ingest(self,query,limit=5):
        if self.web_collector is None:return []
        return [self.ingest(i.get('source','public-web'),i.get('title',''),i.get('snippet',''),i.get('url','')) for i in self.web_collector.search(query,limit)]
    def search(self,query,limit=5):
        terms=[t.lower() for t in query.split() if t.strip()]
        if not terms:return []
        scored=[]
        for document in reversed(self.documents.values()):
            haystack=f'{document.title} {document.text}'.lower(); score=sum(term in haystack for term in terms)
            if score: scored.append((score,document))
        scored.sort(key=lambda item:item[0],reverse=True); return [d for _,d in scored[:limit]]
    def snapshot(self): return {'documents':len(self.documents),'sources':sorted({d.source for d in self.documents.values()})}
