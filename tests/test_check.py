import subprocess
import tempfile
import unittest
from pathlib import Path

from check_backlog import run_checks

HEADER = "| Issue | Title | Status | Spec | PR | ADRs |\n|---|---|---|---|---|---|\n"
ADR_0001 = "# ADR-0001: Record\n\n- **Date:** 2026-11-16\n- **Status:** Accepted\n\n## Context\nOriginal.\n"


ADR_INDEX = "# Decisions\n\n| ADR | Title | Status |\n|---|---|---|\n| [0001](0001-record.md) | Record | Accepted |\n"


def spec(issue: int, tasks: str = "- #57 Add form\n", extra: str = "") -> str:
    return f"# Feature\n\nIssue: #{issue}\n\n## Tasks\n{tasks}\n## Acceptance Criteria\n{extra}\n"


def make_repo(tmp: str, backlog_rows: list[str], specs: dict[str, str] | None = None,
              adrs: dict[str, str] | None = None) -> Path:
    root = Path(tmp)
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "docs" / "BACKLOG.md").write_text("# Backlog\n\n" + HEADER + "".join(r + "\n" for r in backlog_rows))
    for name, text in (specs or {}).items():
        (root / "docs" / "specs" / name).write_text(text)
    for name, text in (adrs or {"0001-record.md": ADR_0001}).items():
        (root / "docs" / "adr" / name).write_text(text)
    if adrs is None:
        (root / "docs" / "adr" / "README.md").write_text(ADR_INDEX)
    return root


def git_commit_all(root: Path) -> None:
    def git(*args):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    git("init", "-q")
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")


class OfflineChecksTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_clean_repo_passes(self):
        root = make_repo(self.tmp, ["| #7 | Login | Specced | [spec](specs/007-login.md) | — | — |"],
                         {"007-login.md": spec(7)})
        self.assertEqual(run_checks(root), [])

    def test_specced_requires_tasks(self):
        root = make_repo(self.tmp, ["| #7 | Login | Specced | [spec](specs/007-login.md) | — | — |"],
                         {"007-login.md": spec(7, tasks="")})
        errors = run_checks(root)
        self.assertEqual(len(errors), 1)
        self.assertIn("no tasks", errors[0])

    def test_malformed_task_line_reported(self):
        root = make_repo(self.tmp, ["| #7 | Login | Specced | [spec](specs/007-login.md) | — | — |"],
                         {"007-login.md": spec(7, tasks="- [ ] #57 Add form\n")})
        self.assertTrue(any("- #N description" in e for e in run_checks(root)))

    def test_done_no_longer_checks_checkboxes(self):
        root = make_repo(self.tmp, ["| #7 | Login | Done | [spec](specs/007-login.md) | #9 | — |"],
                         {"007-login.md": spec(7, extra="- [ ] unticked acceptance item\n")})
        self.assertEqual(run_checks(root), [])

    def test_orphan_spec_and_filename_mismatch(self):
        root = make_repo(self.tmp, ["| #7 | Login | Specced | [spec](specs/008-login.md) | — | — |"],
                         {"008-login.md": spec(7), "012-orphan.md": spec(12)})
        errors = run_checks(root)
        self.assertTrue(any("must start with the issue number" in e for e in errors), errors)
        self.assertTrue(any("no backlog row for #12" in e for e in errors), errors)

    def test_offline_closes_non_done_row(self):
        root = make_repo(self.tmp, ["| #7 | Login | Specced | [spec](specs/007-login.md) | — | — |"],
                         {"007-login.md": spec(7)})
        git_commit_all(root)
        errors = run_checks(root, base_ref="HEAD", pr_number=9, pr_body="Closes #7")
        self.assertEqual(len(errors), 1)
        self.assertIn("Refs #7", errors[0])

    def test_accepted_adr_immutable(self):
        root = make_repo(self.tmp, [])
        git_commit_all(root)
        adr = root / "docs" / "adr" / "0001-record.md"
        adr.write_text(adr.read_text().replace("Original.", "Changed."))
        errors = run_checks(root, base_ref="HEAD", pr_number=9, pr_body="")
        self.assertEqual(len(errors), 1)
        self.assertIn("immutable", errors[0])

    def test_superseding_adr_status_only_is_allowed(self):
        root = make_repo(self.tmp, [])
        git_commit_all(root)
        adr = root / "docs" / "adr" / "0001-record.md"
        adr.write_text(adr.read_text().replace("**Status:** Accepted", "**Status:** Superseded by ADR-0004"))
        self.assertEqual(run_checks(root, base_ref="HEAD", pr_number=9, pr_body=""), [])


if __name__ == "__main__":
    unittest.main()


from tests.fakes import FakeGitHub, make_issue  # noqa: E402

ROW_IN_PROGRESS = "| #42 | Login | In Progress | [spec](specs/042-login.md) | — | — |"
ROW_DONE = "| #42 | Login | Done | [spec](specs/042-login.md) | #60 | — |"


def fake_github(open_tasks=(), closed_tasks=(57, 58), subs=(57, 58), feature_labels=("feature",)):
    issues = {42: make_issue(42, feature_labels)}
    for n in set(open_tasks) | set(closed_tasks) | set(subs):
        state = "closed" if n in closed_tasks else "open"
        issues[n] = make_issue(n, ["task"], state=state, state_reason="completed" if state == "closed" else None)
    return FakeGitHub(issues, subs={42: list(subs)})


class GitHubChecksTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def repo(self, row=ROW_IN_PROGRESS, tasks="- #57 Add form\n- #58 Wire API\n"):
        return make_repo(self.tmp, [row], {"042-login.md": spec(42, tasks=tasks)})

    def test_spec_tasks_match_sub_issues(self):
        root = self.repo()
        gh = fake_github(open_tasks=(57, 58, 59), closed_tasks=(), subs=(57, 59))
        errors = run_checks(root, gh)
        self.assertEqual(len(errors), 2, errors)
        self.assertTrue(any("#58" in e and "not a sub-issue" in e for e in errors), errors)
        self.assertTrue(any("#59" in e and "missing from spec" in e for e in errors), errors)

    def test_matching_spec_and_sub_issues_pass(self):
        self.assertEqual(run_checks(self.repo(), fake_github(open_tasks=(57, 58), closed_tasks=())), [])

    def test_feature_and_task_labels(self):
        gh = fake_github(feature_labels=("bug",))
        gh._issues[58]["labels"] = []
        errors = run_checks(self.repo(), gh)
        self.assertTrue(any("#42" in e and "not labelled feature" in e for e in errors), errors)
        self.assertTrue(any("#58" in e and "not labelled task" in e for e in errors), errors)

    def _done_pr(self, gh, body):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = make_repo(tmp.name, [ROW_IN_PROGRESS], {"042-login.md": spec(42, tasks="- #57 Add form\n- #58 Wire API\n")})
        git_commit_all(root)
        (root / "docs" / "BACKLOG.md").write_text("# Backlog\n\n" + HEADER + ROW_DONE + "\n")
        return run_checks(root, gh, base_ref="HEAD", pr_number=60, pr_body=body)

    def test_done_requires_all_tasks_closed(self):
        ok = self._done_pr(fake_github(open_tasks=(58,), closed_tasks=(57,)), "Closes #58\nCloses #42")
        self.assertEqual(ok, [])
        bad = self._done_pr(fake_github(open_tasks=(57, 58), closed_tasks=()), "Closes #58\nCloses #42")
        self.assertTrue(any("#57" in e and "still open" in e for e in bad), bad)

    def test_closes_feature_without_done(self):
        root = self.repo()
        git_commit_all(root)
        errors = run_checks(root, fake_github(open_tasks=(58,), closed_tasks=(57,)),
                            base_ref="HEAD", pr_number=60, pr_body="Closes #42")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("may only close", errors[0])

    def test_closes_non_task_issue(self):
        root = self.repo()
        git_commit_all(root)
        gh = fake_github()
        gh._issues[70] = make_issue(70, ["bug"])
        errors = run_checks(root, gh, base_ref="HEAD", pr_number=60, pr_body="Fixes #70")
        self.assertTrue(any("#70" in e and "may only close" in e for e in errors), errors)

    def test_closing_a_task_is_allowed(self):
        root = self.repo()
        git_commit_all(root)
        errors = run_checks(root, fake_github(open_tasks=(58,), closed_tasks=(57,)),
                            base_ref="HEAD", pr_number=60, pr_body="Closes #58")
        self.assertEqual(errors, [])

    def test_empty_pr_body(self):
        errors = self._done_pr(fake_github(), None)
        self.assertTrue(any("no 'Closes #42'" in e for e in errors), errors)


class AdrImmutabilityTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = make_repo(tmp.name, [])
        git_commit_all(self.root)
        self.adr = self.root / "docs" / "adr" / "0001-record.md"

    def check(self):
        return run_checks(self.root, base_ref="HEAD", pr_number=9, pr_body="")

    def test_deleting_accepted_adr_is_an_error(self):
        self.adr.unlink()
        errors = self.check()
        self.assertTrue(any("0001-record.md" in e and "deleted or renamed" in e for e in errors), errors)

    def test_accepted_back_to_proposed_is_an_error(self):
        self.adr.write_text(self.adr.read_text().replace("**Status:** Accepted", "**Status:** Proposed"))
        errors = self.check()
        self.assertTrue(any("Superseded by" in e for e in errors), errors)


class DocLimitsAndAdrIndexTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def lines(self, n: int) -> str:
        return "".join(f"line {i}\n" for i in range(n))

    def test_doc_limits_boundary(self):
        root = make_repo(self.tmp, [])
        (root / "README.md").write_text(self.lines(120))
        (root / "CLAUDE.md").write_text(self.lines(150))
        self.assertEqual(run_checks(root), [])
        (root / "README.md").write_text(self.lines(121))
        (root / "CLAUDE.md").write_text(self.lines(151))
        errors = run_checks(root)
        self.assertTrue(any("README.md: 121 lines" in e for e in errors), errors)
        self.assertTrue(any("CLAUDE.md: 151 lines" in e for e in errors), errors)
        self.assertEqual(len(errors), 2, errors)

    def test_doc_limits_skip_missing_files(self):
        self.assertEqual(run_checks(make_repo(self.tmp, [])), [])

    def test_adr_index_missing(self):
        root = make_repo(self.tmp, [], adrs={"0001-record.md": ADR_0001})
        errors = run_checks(root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("not found", errors[0])

    def test_adr_missing_from_index(self):
        second = ADR_0001.replace("ADR-0001: Record", "ADR-0002: Second")
        root = make_repo(self.tmp, [], adrs={"0001-record.md": ADR_0001, "0002-second.md": second})
        (root / "docs" / "adr" / "README.md").write_text(ADR_INDEX)
        errors = run_checks(root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("missing ADR 0002-second.md", errors[0])

    def test_adr_readme_not_treated_as_adr(self):
        root = make_repo(self.tmp, [])
        self.assertTrue((root / "docs" / "adr" / "README.md").is_file())
        self.assertEqual(run_checks(root), [])
