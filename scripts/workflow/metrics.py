"""Task metrics from GitHub data (ADR-0002). Data only: no forecasting."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from workflow.docs import closing_refs

EASTERN = ZoneInfo("America/New_York")
IN_PROGRESS = "status:in-progress"


def _ts(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


@dataclass
class TaskRecord:
    number: int
    title: str
    feature: int | None
    discovered: bool
    state: str
    state_reason: str | None
    created: datetime
    first_started: datetime | None
    last_started: datetime | None
    closed: datetime | None
    pr: int | None
    in_progress_now: bool = False

    @property
    def completed(self) -> bool:
        return self.state == "closed" and self.state_reason == "completed"

    @property
    def cycle_days(self) -> float | None:
        if not self.completed or self.first_started is None or self.closed is None:
            return None
        if self.first_started > self.closed:  # label added retroactively; listed in the audit instead
            return None
        return round((self.closed - self.first_started).total_seconds() / 86400, 2)


def started_times(timeline: list[dict]) -> tuple[datetime | None, datetime | None]:
    """First and last time the in-progress label was added."""
    times = sorted(_ts(e["created_at"]) for e in timeline
                   if e.get("event") == "labeled" and (e.get("label") or {}).get("name") == IN_PROGRESS)
    return (times[0], times[-1]) if times else (None, None)


def linked_pr(timeline: list[dict], task: int, repo: str | None = None) -> int | None:
    """The first merged PR in this repo that references this task with a closing keyword."""
    for e in timeline:
        if e.get("event") != "cross-referenced":
            continue
        source = (e.get("source") or {}).get("issue") or {}
        pr = source.get("pull_request") or {}
        source_repo = (source.get("repository") or {}).get("full_name")
        if repo and source_repo and source_repo.lower() != repo.lower():
            continue
        if pr.get("merged_at") and task in closing_refs(source.get("body"), repo):
            return source.get("number")
    return None


def collect(gh) -> list[TaskRecord]:
    """One record per issue labelled `task`, with its parent feature and timeline data."""
    parent: dict[int, int] = {}
    for feature in gh.issues("feature"):
        for sub in gh.sub_issues(feature["number"]):
            parent[sub["number"]] = feature["number"]

    records = []
    for issue in gh.issues("task"):
        n = issue["number"]
        labels = {lb["name"] for lb in issue.get("labels", [])}
        timeline = gh.timeline(n)
        first, last = started_times(timeline)
        records.append(TaskRecord(
            number=n,
            title=issue.get("title", ""),
            feature=parent.get(n),
            discovered="discovered" in labels,
            state=issue.get("state", "open"),
            state_reason=issue.get("state_reason"),
            created=_ts(issue["created_at"]),
            first_started=first,
            last_started=last,
            closed=_ts(issue.get("closed_at")),
            pr=linked_pr(timeline, n, getattr(gh, "repo", None)),
            in_progress_now=issue.get("state") == "open" and IN_PROGRESS in labels,
        ))
    return sorted(records, key=lambda r: r.number)


def _week_start(moment: datetime) -> date:
    local = moment.astimezone(EASTERN).date()
    return local - timedelta(days=local.weekday())


def weekly_throughput(records: list[TaskRecord], now: datetime, since: date | None = None) -> list[tuple[date, int]]:
    """Completed tasks per ISO week (Monday start, US Eastern), zero weeks included."""
    counts: dict[date, int] = {}
    for r in records:
        if r.completed and r.closed:
            week = _week_start(r.closed)
            counts[week] = counts.get(week, 0) + 1
    if since is not None:
        first = since - timedelta(days=since.weekday())
    elif counts:
        first = min(counts)
    else:
        return []
    last = _week_start(now)
    weeks = []
    week = first
    while week <= last:
        weeks.append((week, counts.get(week, 0)))
        week += timedelta(days=7)
    return weeks


def cycle_summary(records: list[TaskRecord]) -> dict:
    values = [r.cycle_days for r in records if r.cycle_days is not None]
    if not values:
        return {"count": 0, "median": None, "mean": None, "min": None, "max": None}
    return {"count": len(values), "median": round(statistics.median(values), 2),
            "mean": round(statistics.mean(values), 2), "min": min(values), "max": max(values)}


def discovered_counts(records: list[TaskRecord]) -> dict[int | None, tuple[int, int]]:
    """Per feature: (planned, discovered), over all tasks."""
    out: dict[int | None, list[int]] = {}
    for r in records:
        pair = out.setdefault(r.feature, [0, 0])
        pair[1 if r.discovered else 0] += 1
    return {k: (v[0], v[1]) for k, v in out.items()}


def remaining(records: list[TaskRecord]) -> dict[int | None, tuple[int, int]]:
    """Per feature: (to do, in progress), over open tasks."""
    out: dict[int | None, list[int]] = {}
    for r in records:
        if r.state != "open":
            continue
        pair = out.setdefault(r.feature, [0, 0])
        pair[1 if r.in_progress_now else 0] += 1
    return {k: (v[0], v[1]) for k, v in out.items()}


def audit(records: list[TaskRecord]) -> list[str]:
    problems = []
    for r in records:
        if r.completed and r.pr is None:
            problems.append(f"#{r.number} closed as completed with no linked PR")
        if r.feature is None:
            problems.append(f"#{r.number} has no parent feature")
        if r.completed and r.first_started is None:
            problems.append(f"#{r.number} completed but never labelled status:in-progress")
        elif r.completed and r.closed and r.first_started > r.closed:
            problems.append(f"#{r.number} first labelled status:in-progress after it closed")
    return problems
