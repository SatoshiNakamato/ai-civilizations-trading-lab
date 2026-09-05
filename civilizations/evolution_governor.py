"""Governed autonomy for agent-created memory and evolution proposals.

Agents may create persistent artifacts, but they never receive unrestricted
filesystem or repository authority. The governor validates every operation,
keeps writes inside explicit namespaces, limits resource usage, and records an
append-only audit trail. Source-code changes are proposals only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class EvolutionGovernorConfig:
    workspace: Path
    max_file_bytes: int = 64_000
    max_total_bytes: int = 5_000_000
    max_files: int = 500
    allow_memory: bool = True
    allow_proposals: bool = True
    allow_docs: bool = True

    @classmethod
    def from_env(cls, workspace: str | Path | None = None) -> "EvolutionGovernorConfig":
        root = Path(workspace or os.getenv("AEON_EVOLUTION_WORKSPACE", "data/evolution"))
        return cls(
            workspace=root,
            max_file_bytes=max(1024, int(os.getenv("AEON_EVOLUTION_MAX_FILE_BYTES", "64000"))),
            max_total_bytes=max(1024, int(os.getenv("AEON_EVOLUTION_MAX_TOTAL_BYTES", "5000000"))),
            max_files=max(1, int(os.getenv("AEON_EVOLUTION_MAX_FILES", "500"))),
            allow_memory=_flag("AEON_EVOLUTION_ALLOW_MEMORY", True),
            allow_proposals=_flag("AEON_EVOLUTION_ALLOW_PROPOSALS", True),
            allow_docs=_flag("AEON_EVOLUTION_ALLOW_DOCS", True),
        )


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EvolutionWrite:
    agent_id: str
    path: str
    kind: str
    sha256: str
    bytes_written: int
    timestamp: float


class EvolutionGovernor:
    """Policy boundary for persistent agent creativity."""

    NAMESPACES = {
        "memory": "world_artifacts/agent_memory",
        "proposal": "world_artifacts/agent_proposals",
        "doc": "docs/agent-evolution",
    }

    def __init__(self, config: EvolutionGovernorConfig | None = None):
        self.config = config or EvolutionGovernorConfig.from_env()
        self.root = self.config.workspace.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.audit_path = self.root / "evolution_audit.jsonl"

    def _namespace_enabled(self, kind: str) -> bool:
        return {
            "memory": self.config.allow_memory,
            "proposal": self.config.allow_proposals,
            "doc": self.config.allow_docs,
        }.get(kind, False)

    def _safe_relative(self, kind: str, relative: str) -> Path:
        if kind not in self.NAMESPACES or not self._namespace_enabled(kind):
            raise PermissionError(f"evolution namespace disabled: {kind}")
        relative = relative.strip().replace("\\", "/")
        parts = Path(relative).parts
        if not parts or any(p in {"", ".", ".."} or not _SAFE_COMPONENT.fullmatch(p) for p in parts):
            raise ValueError("unsafe evolution path")
        target = (self.root / self.NAMESPACES[kind] / Path(*parts)).resolve()
        base = (self.root / self.NAMESPACES[kind]).resolve()
        if target != base and base not in target.parents:
            raise PermissionError("evolution path escaped namespace")
        return target

    def _usage(self) -> tuple[int, int]:
        total = 0
        files = 0
        for base in (self.root / n for n in self.NAMESPACES.values()):
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if path.is_file() and not path.is_symlink():
                    files += 1
                    total += path.stat().st_size
        return files, total

    def write(self, agent_id: str, kind: str, relative: str, content: str) -> EvolutionWrite:
        if not agent_id or len(agent_id) > 128:
            raise ValueError("invalid agent id")
        if not isinstance(content, str):
            raise TypeError("content must be text")
        data = content.encode("utf-8")
        if len(data) > self.config.max_file_bytes:
            raise ValueError("evolution artifact exceeds per-file limit")
        target = self._safe_relative(kind, relative)
        if target.exists() and target.is_symlink():
            raise PermissionError("symlink targets are forbidden")
        files, total = self._usage()
        if not target.exists() and files >= self.config.max_files:
            raise RuntimeError("evolution file quota exhausted")
        old = target.stat().st_size if target.exists() else 0
        if total - old + len(data) > self.config.max_total_bytes:
            raise RuntimeError("evolution storage quota exhausted")
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(target)
        record = EvolutionWrite(agent_id, str(target.relative_to(self.root)), kind,
                                 hashlib.sha256(data).hexdigest(), len(data), time.time())
        with self.audit_path.open("a", encoding="utf-8") as audit:
            audit.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record

    def read(self, kind: str, relative: str) -> str:
        target = self._safe_relative(kind, relative)
        if not target.exists() or not target.is_file() or target.is_symlink():
            raise FileNotFoundError(relative)
        return target.read_text(encoding="utf-8")

    def list(self, kind: str, agent_id: str | None = None) -> list[str]:
        base = (self.root / self.NAMESPACES.get(kind, "")).resolve()
        if kind not in self.NAMESPACES or not self._namespace_enabled(kind):
            raise PermissionError(f"evolution namespace disabled: {kind}")
        if not base.exists():
            return []
        prefix = f"{agent_id}/" if agent_id else ""
        return sorted(
            str(p.relative_to(base)).replace(os.sep, "/")
            for p in base.rglob("*")
            if p.is_file() and not p.is_symlink() and str(p.relative_to(base)).replace(os.sep, "/").startswith(prefix)
        )

    def propose_source_change(self, agent_id: str, title: str, rationale: str, patch: str) -> EvolutionWrite:
        """Persist a source-change proposal without granting source write access."""
        if not title.strip() or not rationale.strip() or not patch.strip():
            raise ValueError("proposal requires title, rationale and patch")
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", title.strip()).strip("-").lower()[:80]
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        payload = json.dumps({
            "title": title.strip(),
            "rationale": rationale.strip(),
            "patch": patch,
            "source_write": False,
            "requires_human_review": True,
        }, indent=2, sort_keys=True)
        return self.write(agent_id, "proposal", f"{agent_id}/{stamp}-{slug}.json", payload)


__all__ = ["EvolutionGovernor", "EvolutionGovernorConfig", "EvolutionWrite"]
