#!/usr/bin/env python3
"""Task report from GitHub data: throughput, time per task, discovered and remaining tasks.

Data only, no forecasts (ADR-0002). Weeks are Monday-Sunday, US Eastern time.

    python scripts/report.py [--feature N] [--since YYYY-MM-DD] [--csv PATH]

Write CSV output OUTSIDE the repository: it contains task titles, and *.csv is blocked from commits.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workflow.metrics import (  # noqa: E402
    EASTERN, TaskRecord, audit, collect, cycle_summary, discovered_counts, remaining, weekly_throughput,
)

ROOT = Path(__file__).resolve().parent.parent
CSV_COLUMNS = ["task", "title", "feature", "discovered", "state", "state_reason", "created",
               "first_started", "last_started", "closed", "cycle_days", "pr"]


def _feature_label(feature: int | None) -> str:
    return f"#{feature}" if feature is not None else "(no feature)"


def _sorted_features(keys) -> list:
    return sorted(keys, key=lambda f: (f is None, f or 0))


def _local(moment: datetime | None) -> str:
    return moment.astimezone(EASTERN).isoformat() if moment else ""


def render(records: list[TaskRecord], now: datetime, since: date | None) -> str:
    out: list[str] = []

    out.append("Tasks finished per week (week starting Monday, US Eastern)")
    weeks = weekly_throughput(records, now, since)
    out += [f"  {week.isoformat()}  {count}" for week, count in weeks] or ["  none"]

    out += ["", "Time per task (in progress → done, days)"]
    s = cycle_summary(records)
    if s["count"]:
        out.append(f"  count {s['count']}  median {s['median']}  mean {s['mean']}  "
                   f"min {s['min']}  max {s['max']}")
        out += [f"  #{r.number}  {r.cycle_days}  {r.title}" for r in records if r.cycle_days is not None]
    else:
        out.append("  none")

    out += ["", "Discovered tasks (planned / discovered)"]
    counts = discovered_counts(records)
    for f in _sorted_features(counts):
        planned, found = counts[f]
        out.append(f"  {_feature_label(f)}  {planned} planned  {found} discovered")
    if counts:
        out.append(f"  total  {sum(v[0] for v in counts.values())} planned  "
                   f"{sum(v[1] for v in counts.values())} discovered")
    else:
        out.append("  none")

    out += ["", "Remaining tasks (to do / in progress)"]
    rem = remaining(records)
    out += [f"  {_feature_label(f)}  {rem[f][0]} to do  {rem[f][1]} in progress"
            for f in _sorted_features(rem)] or ["  none"]

    out += ["", "Audit"]
    out += [f"  {p}" for p in audit(records)] or ["  none"]
    return "\n".join(out) + "\n"


def write_csv(records: list[TaskRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)
        for r in records:
            writer.writerow([
                r.number, r.title, "" if r.feature is None else r.feature,
                "true" if r.discovered else "false", r.state, r.state_reason or "",
                _local(r.created), _local(r.first_started), _local(r.last_started), _local(r.closed),
                "" if r.cycle_days is None else r.cycle_days, "" if r.pr is None else r.pr,
            ])


def main(argv: list[str] | None = None, gh=None, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feature", type=int, help="only tasks of this feature issue")
    ap.add_argument("--since", type=date.fromisoformat, help="first week to show (YYYY-MM-DD)")
    ap.add_argument("--csv", type=Path, help="also write one row per task to this CSV file")
    args = ap.parse_args(argv)

    if gh is None:
        from workflow.github import GitHub, repo_slug
        gh = GitHub(repo_slug(ROOT))
    records = collect(gh)
    if args.feature is not None:
        records = [r for r in records if r.feature == args.feature]
    print(render(records, now or datetime.now(timezone.utc), args.since), end="")
    if args.csv:
        write_csv(records, args.csv)
        print(f"\nCSV written to {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
