"""Thin GitHub REST client over `gh api`. REST only: GraphQL is blocked in Claude Code cloud sessions."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


def repo_slug(root: Path) -> str:
    """`owner/repo` from $GITHUB_REPOSITORY, or else from the `origin` remote URL."""
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env
    url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=root,
                         capture_output=True, text=True, check=True).stdout.strip()
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        raise RuntimeError(f"cannot work out owner/repo from remote URL {url!r}")
    return f"{m.group(1)}/{m.group(2)}"


class GitHub:
    def __init__(self, repo: str, runner=subprocess.run):
        self.repo = repo
        self._run = runner

    def _api(self, *args: str):
        res = self._run(["gh", "api", *args], capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"gh api {' '.join(args)} failed: {res.stderr.strip()}")
        return json.loads(res.stdout or "null")

    def _list(self, path: str) -> list[dict]:
        pages = self._api("--paginate", "--slurp", path) or []
        return [item for page in pages for item in page]

    def issue(self, n: int) -> dict:
        return self._api(f"repos/{self.repo}/issues/{n}")

    def sub_issues(self, n: int) -> list[dict]:
        return self._list(f"repos/{self.repo}/issues/{n}/sub_issues?per_page=100")

    def issues(self, label: str) -> list[dict]:
        """All issues (open and closed) with this label. Pull requests are excluded."""
        items = self._list(f"repos/{self.repo}/issues?labels={label}&state=all&per_page=100")
        return [i for i in items if "pull_request" not in i]

    def timeline(self, n: int) -> list[dict]:
        return self._list(f"repos/{self.repo}/issues/{n}/timeline?per_page=100")
