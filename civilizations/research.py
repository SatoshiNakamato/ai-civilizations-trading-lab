from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable


@dataclass(frozen=True)
class ResearchDocument:
    source: str
    title: str
    text: str
    digest: str


class ResearchDesk:
    """Source-aware research inbox for the civilization.

    Documents are supplied by an external data collector. The civilization
    can therefore learn from real research without giving its agents the
    ability to execute trades or take unrestricted external actions.
    """

    def __init__(self, allowed_sources: Iterable[str] | None = None):
        self.allowed_sources = set(allowed_sources or ())
        self.documents: dict[str, ResearchDocument] = {}

    def ingest(self, source: str, title: str, text: str) -> ResearchDocument:
        if self.allowed_sources and source not in self.allowed_sources:
            raise ValueError("research source is not allowlisted")
        clean = " ".join(text.split())
        digest = sha256(f"{source}\n{title}\n{clean}".encode()).hexdigest()
        document = ResearchDocument(source, title, clean, digest)
        self.documents[digest] = document
        return document

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
