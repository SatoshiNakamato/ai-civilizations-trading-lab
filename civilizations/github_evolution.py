"""Optional GitHub persistence bridge for governed civilization artifacts.

The worker can persist agent memory/proposals to a dedicated branch without
receiving unrestricted repository control. Source-code paths are rejected by
policy. A fine-grained GitHub token should be supplied only through the
runtime environment and should have repository Contents read/write access;
it is never written to civilization state.
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .evolution_governor import EvolutionGovernor


@dataclass(frozen=True)
class GitHubEvolutionConfig:
    repo: str
    token: str
    base_branch: str = "main"
    branch_prefix: str = "aeon/agent-memory-"
    api_url: str = "https://api.github.com"

    @classmethod
    def from_env(cls) -> "GitHubEvolutionConfig | None":
        token = os.getenv("AEON_GITHUB_TOKEN", "").strip()
        repo = os.getenv("AEON_GITHUB_REPO", "SatoshiNakamato/ai-civilizations-trading-lab").strip()
        if not token or not repo:
            return None
        return cls(repo=repo, token=token, base_branch=os.getenv("AEON_GITHUB_BASE_BRANCH", "main"))


class GitHubEvolutionPublisher:
    """Publish only governed artifact namespaces to a fresh Git branch."""

    ALLOWED_PREFIXES = (
        "world_artifacts/agent_memory/",
        "world_artifacts/agent_proposals/",
        "docs/agent-evolution/",
    )
    BLOCKED_NAMES = {".github", "execution", "risk", "markets", "civilizations", "simulation", "backtesting", "web"}

    def __init__(self, config: GitHubEvolutionConfig):
        self.config = config
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", config.repo):
            raise ValueError("invalid GitHub repository")

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        url = self.config.api_url.rstrip("/") + path
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, method=method, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.config.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "AEON-evolution-governor",
        })
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"GitHub API {exc.code}: {detail}") from exc

    def _allowed(self, relative: str) -> bool:
        path = relative.replace("\\", "/").lstrip("/")
        if ".." in Path(path).parts:
            return False
        return path.startswith(self.ALLOWED_PREFIXES)

    def publish(self, governor: EvolutionGovernor, *, branch: str, message: str) -> str:
        """Commit current governed artifacts to a non-main branch."""
        if branch == self.config.base_branch or not branch.startswith(self.config.branch_prefix):
            raise PermissionError("GitHub evolution publisher may only use an AEON branch")
        files: list[tuple[str, bytes]] = []
        for kind in ("memory", "proposal", "doc"):
            for relative in governor.list(kind):
                if not self._allowed(relative):
                    raise PermissionError(f"blocked repository path: {relative}")
                data = governor.read(kind, relative).encode("utf-8")
                files.append((relative, data))
        if not files:
            raise ValueError("no governed artifacts to publish")

        ref = self._request("GET", f"/repos/{self.config.repo}/git/ref/heads/{self.config.base_branch}")
        base_sha = ref["object"]["sha"]
        self._request("POST", f"/repos/{self.config.repo}/git/refs", {
            "ref": f"refs/heads/{branch}", "sha": base_sha
        })

        tree = []
        for path, data in files:
            blob = self._request("POST", f"/repos/{self.config.repo}/git/blobs", {
                "content": base64.b64encode(data).decode("ascii"), "encoding": "base64"
            })
            tree.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree_obj = self._request("POST", f"/repos/{self.config.repo}/git/trees", {
            "base_tree": base_sha, "tree": tree
        })
        commit = self._request("POST", f"/repos/{self.config.repo}/git/commits", {
            "message": message, "tree": tree_obj["sha"], "parents": [base_sha]
        })
        self._request("PATCH", f"/repos/{self.config.repo}/git/refs/heads/{branch}", {
            "sha": commit["sha"], "force": False
        })
        return commit["sha"]


__all__ = ["GitHubEvolutionConfig", "GitHubEvolutionPublisher"]
