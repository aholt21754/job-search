import contextlib
import csv
import io
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from report import main, render, write_csv
from tests.fakes import FakeGitHub, make_issue
from workflow.metrics import collect

NOW = datetime(2026, 11, 18, 15, tzinfo=timezone.utc)
HEADER = ["task", "title", "feature", "discovered", "state", "state_reason", "created",
          "first_started", "last_started", "closed", "cycle_days", "pr"]


def fake() -> FakeGitHub:
    issues = {
        42: make_issue(42, ["feature"]),
        43: make_issue(43, ["feature"]),
        57: make_issue(57, ["task"], state="closed", state_reason="completed",
                       closed_at="2026-11-09T04:30:00Z", title="Add form"),
        58: make_issue(58, ["task", "discovered", "status:in-progress"], title="Wire API"),
        70: make_issue(70, ["task"], title="Other feature task"),
    }
    timelines = {57: [{"event": "labeled", "created_at": "2026-11-06T14:00:00Z",
                       "label": {"name": "status:in-progress"}},
                      {"event": "cross-referenced", "created_at": "2026-11-08T10:00:00Z",
                       "source": {"issue": {"number": 61, "body": "Closes #57",
                                            "pull_request": {"merged_at": "2026-11-09T04:29:00Z"}}}}]}
    return FakeGitHub(issues, subs={42: [57, 58], 43: [70]}, timelines=timelines)


class RenderTest(unittest.TestCase):
    def test_render_sections_in_order(self):
        out = render(collect(fake()), NOW, None)
        headings = ["Tasks finished per week", "Time per task (in progress → done, days)",
                    "Discovered tasks", "Remaining tasks", "Audit"]
        positions = [out.index(h) for h in headings]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("#42", out)
        self.assertIn("2026-11-02", out)  # the week of the Sunday-night close

    def test_render_empty_audit_says_none(self):
        recs = [r for r in collect(fake()) if r.number == 57]
        self.assertTrue(render(recs, NOW, None).rstrip().endswith("none"))


class CsvTest(unittest.TestCase):
    def test_csv_header_and_eastern_times(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            write_csv(collect(fake()), path)
            rows = list(csv.reader(path.open()))
        self.assertEqual(rows[0], HEADER)
        row57 = dict(zip(HEADER, next(r for r in rows[1:] if r[0] == "57")))
        self.assertEqual(row57["closed"], "2026-11-08T23:30:00-05:00")
        self.assertEqual(row57["first_started"], "2026-11-06T09:00:00-05:00")
        self.assertEqual(row57["cycle_days"], "2.6")
        self.assertEqual(row57["pr"], "61")
        self.assertEqual(row57["feature"], "42")
        row58 = dict(zip(HEADER, next(r for r in rows[1:] if r[0] == "58")))
        self.assertEqual(row58["closed"], "")
        self.assertEqual(row58["discovered"], "true")


class CsvFolderTest(unittest.TestCase):
    def test_csv_creates_missing_parent_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "job-search-data" / "reports" / "tasks.csv"
            write_csv(collect(fake()), path)
            self.assertTrue(path.is_file())


class MainTest(unittest.TestCase):
    def run_main(self, *argv) -> str:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(main(list(argv), gh=fake(), now=NOW), 0)
        return buf.getvalue()

    def test_feature_filter(self):
        out = self.run_main("--feature", "42")
        self.assertIn("#42", out)
        self.assertNotIn("#43", out)

    def test_csv_flag_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.csv"
            self.run_main("--csv", str(path))
            self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
