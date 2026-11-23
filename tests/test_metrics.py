import unittest
from datetime import date, datetime, timezone

from tests.fakes import FakeGitHub, make_issue
from workflow.metrics import (
    audit, collect, cycle_summary, discovered_counts, linked_pr, remaining, started_times, weekly_throughput,
)


def labeled(at: str, name: str = "status:in-progress") -> dict:
    return {"event": "labeled", "created_at": at, "label": {"name": name}}


def unlabeled(at: str, name: str = "status:in-progress") -> dict:
    return {"event": "unlabeled", "created_at": at, "label": {"name": name}}


def xref(pr: int, body: str | None, merged: bool = True) -> dict:
    return {"event": "cross-referenced", "created_at": "2026-11-05T10:00:00Z",
            "source": {"type": "issue", "issue": {
                "number": pr, "body": body,
                "pull_request": {"merged_at": "2026-11-05T13:00:00Z" if merged else None}}}}


def utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def world(tasks: dict[int, dict], timelines: dict[int, list[dict]], feature_subs: dict[int, list[int]]):
    issues = {n: make_issue(n, ["feature"]) for n in feature_subs}
    issues.update(tasks)
    return FakeGitHub(issues, subs=feature_subs, timelines=timelines)


def done_task(n: int, closed: str, labels=("task",), reason: str = "completed") -> dict:
    return make_issue(n, labels, state="closed", state_reason=reason, closed_at=closed)


NOW = utc("2026-11-18T15:00:00Z")


class StartedTimesTest(unittest.TestCase):
    def test_restart_uses_first_start(self):
        tl = [labeled("2026-11-02T14:00:00Z"), unlabeled("2026-11-03T14:00:00Z"),
              labeled("2026-11-04T14:00:00Z"), labeled("2026-11-04T15:00:00Z", "other")]
        self.assertEqual(started_times(tl), (utc("2026-11-02T14:00:00Z"), utc("2026-11-04T14:00:00Z")))
        gh = world({57: done_task(57, "2026-11-05T14:00:00Z")}, {57: tl + [xref(61, "Closes #57")]}, {42: [57]})
        [rec] = collect(gh)
        self.assertEqual(rec.first_started, utc("2026-11-02T14:00:00Z"))
        self.assertEqual(rec.last_started, utc("2026-11-04T14:00:00Z"))
        self.assertEqual(rec.cycle_days, 3.0)

    def test_never_started(self):
        self.assertEqual(started_times([]), (None, None))


class ThroughputTest(unittest.TestCase):
    def records(self, closes: list[str], reason: str = "completed"):
        tasks = {n: done_task(n, c, reason=reason) for n, c in enumerate(closes, start=57)}
        return collect(world(tasks, {}, {42: list(tasks)}))

    def test_sunday_night_eastern_counts_in_that_week(self):
        recs = self.records(["2026-11-09T04:30:00Z"])  # Sunday 8 Nov, 11:30pm EST
        self.assertEqual(weekly_throughput(recs, NOW)[0], (date(2026, 11, 2), 1))

    def test_dst_boundary(self):
        recs = self.records(["2026-11-02T04:30:00Z"])  # Sunday 1 Nov, 11:30pm EST (DST ended that morning)
        self.assertEqual(weekly_throughput(recs, NOW)[0], (date(2026, 10, 26), 1))

    def test_zero_weeks_included(self):
        recs = self.records(["2026-11-03T15:00:00Z", "2026-11-17T15:00:00Z"])
        self.assertEqual(weekly_throughput(recs, NOW),
                         [(date(2026, 11, 2), 1), (date(2026, 11, 9), 0), (date(2026, 11, 16), 1)])

    def test_since_starts_earlier(self):
        recs = self.records(["2026-11-17T15:00:00Z"])
        self.assertEqual(weekly_throughput(recs, NOW, since=date(2026, 11, 12)),
                         [(date(2026, 11, 9), 0), (date(2026, 11, 16), 1)])

    def test_no_completions(self):
        self.assertEqual(weekly_throughput([], NOW), [])

    def test_not_planned_excluded(self):
        tasks = {57: done_task(57, "2026-11-05T14:00:00Z", reason="not_planned")}
        recs = collect(world(tasks, {57: [labeled("2026-11-02T14:00:00Z")]}, {42: [57]}))
        self.assertEqual(weekly_throughput(recs, NOW), [])
        self.assertEqual(cycle_summary(recs)["count"], 0)
        self.assertEqual(recs[0].cycle_days, None)


class CycleSummaryTest(unittest.TestCase):
    def test_summary_values(self):
        tasks, tls = {}, {}
        for n, (start, end) in {57: ("2026-11-02", "2026-11-03"), 58: ("2026-11-02", "2026-11-05"),
                                59: ("2026-11-02", "2026-11-04")}.items():
            tasks[n] = done_task(n, f"{end}T14:00:00Z")
            tls[n] = [labeled(f"{start}T14:00:00Z")]
        s = cycle_summary(collect(world(tasks, tls, {42: list(tasks)})))
        self.assertEqual(s, {"count": 3, "median": 2.0, "mean": 2.0, "min": 1.0, "max": 3.0})

    def test_empty(self):
        self.assertEqual(cycle_summary([]), {"count": 0, "median": None, "mean": None, "min": None, "max": None})


class LinkedPrAndAuditTest(unittest.TestCase):
    def test_linked_pr_and_audit(self):
        self.assertIsNone(linked_pr([xref(61, "Closes #57", merged=False)], 57))
        self.assertEqual(linked_pr([xref(60, "Refs #57"), xref(61, "Closes #57")], 57), 61)
        self.assertIsNone(linked_pr([xref(61, None)], 57))

        tasks = {57: done_task(57, "2026-11-05T14:00:00Z"), 58: done_task(58, "2026-11-05T14:00:00Z")}
        tls = {57: [labeled("2026-11-02T14:00:00Z"), xref(61, "Closes #57", merged=False)],
               58: [labeled("2026-11-02T14:00:00Z"), xref(62, "Closes #58")]}
        recs = {r.number: r for r in collect(world(tasks, tls, {42: [57, 58]}))}
        self.assertIsNone(recs[57].pr)
        self.assertEqual(recs[58].pr, 62)
        problems = audit(list(recs.values()))
        self.assertEqual(problems, ["#57 closed as completed with no linked PR"])

    def test_hand_closed_task_still_counts_in_throughput(self):
        recs = collect(world({57: done_task(57, "2026-11-17T14:00:00Z")}, {}, {42: [57]}))
        self.assertEqual(weekly_throughput(recs, NOW), [(date(2026, 11, 16), 1)])
        self.assertIn("#57 closed as completed with no linked PR", audit(recs))
        self.assertIn("#57 completed but never labelled status:in-progress", audit(recs))

    def test_orphan_task(self):
        gh = FakeGitHub({57: make_issue(57, ["task"])})
        self.assertEqual(audit(collect(gh)), ["#57 has no parent feature"])


class DiscoveredAndRemainingTest(unittest.TestCase):
    def test_discovered_and_remaining(self):
        tasks = {57: done_task(57, "2026-11-05T14:00:00Z"),
                 58: make_issue(58, ["task", "discovered", "status:in-progress"]),
                 59: make_issue(59, ["task"])}
        recs = collect(world(tasks, {}, {42: [57, 58, 59]}))
        self.assertEqual(discovered_counts(recs), {42: (2, 1)})
        self.assertEqual(remaining(recs), {42: (1, 1)})
        by_number = {r.number: r for r in recs}
        self.assertTrue(by_number[58].discovered)
        self.assertTrue(by_number[58].in_progress_now)


if __name__ == "__main__":
    unittest.main()


class RepoAndRetroactiveLabelTest(unittest.TestCase):
    def test_linked_pr_ignores_other_repositories(self):
        other = xref(61, "Closes #57")
        other["source"]["issue"]["repository"] = {"full_name": "someone/else"}
        ours = xref(62, "Closes https://github.com/o/r/issues/57")
        ours["source"]["issue"]["repository"] = {"full_name": "o/r"}
        self.assertEqual(linked_pr([other, ours], 57, "o/r"), 62)

    def test_label_added_after_close_gives_no_cycle_time(self):
        tasks = {57: done_task(57, "2026-11-05T14:00:00Z")}
        recs = collect(world(tasks, {57: [labeled("2026-11-06T14:00:00Z"), xref(61, "Closes #57")]}, {42: [57]}))
        self.assertIsNone(recs[0].cycle_days)
        self.assertEqual(cycle_summary(recs)["count"], 0)
        self.assertIn("#57 first labelled status:in-progress after it closed", audit(recs))
