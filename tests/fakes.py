"""Test doubles for workflow.github.GitHub. Made-up data only."""
from __future__ import annotations


def make_issue(number: int, labels=(), state: str = "open", state_reason: str | None = None,
               created_at: str = "2026-11-02T14:00:00Z", closed_at: str | None = None,
               title: str | None = None, body: str | None = "") -> dict:
    return {
        "number": number,
        "id": 1000 + number,
        "title": title or f"Issue {number}",
        "labels": [{"name": name} for name in labels],
        "state": state,
        "state_reason": state_reason,
        "created_at": created_at,
        "closed_at": closed_at,
        "body": body,
    }


class FakeGitHub:
    """Same interface as GitHub, served from dictionaries."""

    repo = "o/r"

    def __init__(self, issues: dict[int, dict], subs: dict[int, list[int]] | None = None,
                 timelines: dict[int, list[dict]] | None = None):
        self._issues = issues
        self._subs = subs or {}
        self._timelines = timelines or {}

    def issue(self, n: int) -> dict:
        if n not in self._issues:
            raise RuntimeError(f"gh api repos/o/r/issues/{n} failed: Not Found")
        return self._issues[n]

    def sub_issues(self, n: int) -> list[dict]:
        return [self._issues[s] for s in self._subs.get(n, [])]

    def issues(self, label: str) -> list[dict]:
        return [i for i in self._issues.values() if label in {lb["name"] for lb in i["labels"]}]

    def timeline(self, n: int) -> list[dict]:
        return self._timelines.get(n, [])
