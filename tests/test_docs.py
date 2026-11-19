import unittest

from workflow.docs import SpecTask, closing_refs, parse_backlog, parse_spec_tasks


def spec_with_tasks(body: str) -> str:
    return f"# Title\n\nIssue: #42\n\n## Tasks\n{body}\n## Acceptance Criteria\n- [ ] works\n"


class ParseSpecTasksTest(unittest.TestCase):
    def test_parse_spec_tasks_reads_lines(self):
        tasks, errors = parse_spec_tasks(spec_with_tasks("- #57 Add form\n- #58 Wire API\n"))
        self.assertEqual(tasks, [SpecTask(57, "Add form"), SpecTask(58, "Wire API")])
        self.assertEqual(errors, [])

    def test_parse_spec_tasks_rejects_checkbox(self):
        tasks, errors = parse_spec_tasks(spec_with_tasks("- [ ] #57 Add form\n"))
        self.assertEqual(tasks, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("- #N description", errors[0])

    def test_parse_spec_tasks_duplicate(self):
        _, errors = parse_spec_tasks(spec_with_tasks("- #57 Add form\n- #57 Again\n"))
        self.assertEqual(len(errors), 1)
        self.assertIn("#57", errors[0])

    def test_parse_spec_tasks_stops_at_next_heading(self):
        text = "## Tasks\n- #57 Add form\n## Acceptance Criteria\n- [ ] not a task line\n- #99 also not a task\n"
        tasks, errors = parse_spec_tasks(text)
        self.assertEqual(tasks, [SpecTask(57, "Add form")])
        self.assertEqual(errors, [])

    def test_parse_spec_tasks_ignores_prose_lines_that_are_not_list_items(self):
        tasks, errors = parse_spec_tasks(spec_with_tasks("Tasks are a day or less.\n\n- #57 Add form\n"))
        self.assertEqual(tasks, [SpecTask(57, "Add form")])
        self.assertEqual(errors, [])


class ClosingRefsTest(unittest.TestCase):
    def test_closing_refs(self):
        body = "Closes #5, fixes #6. Refs #7. resolved: #8 other/repo#9"
        self.assertEqual(closing_refs(body), {5, 6, 8})

    def test_closing_refs_none(self):
        self.assertEqual(closing_refs(None), set())


class ParseBacklogTest(unittest.TestCase):
    def test_parse_backlog_ignores_comment_rows(self):
        text = (
            "| Issue | Title | Status | Spec | PR | ADRs |\n"
            "|---|---|---|---|---|---|\n"
            "<!--\n| #9 | Example | Proposed | — | — | — |\n-->\n"
            "| #3 | Real | Proposed | — | — | — |\n"
        )
        rows, errors = parse_backlog(text, "BACKLOG")
        self.assertEqual(sorted(rows), [3])
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()


class ClosingRefsRepoFormsTest(unittest.TestCase):
    def test_same_repo_slug_and_url_forms(self):
        body = ("Closes aholt21754/job-search#42\n"
                "Fixes https://github.com/aholt21754/job-search/issues/43\n"
                "Closes other/repo#44\nresolves https://github.com/other/repo/issues/45\nCloses #46")
        self.assertEqual(closing_refs(body, "aholt21754/job-search"), {42, 43, 46})
        self.assertEqual(closing_refs(body, "AHOLT21754/Job-Search"), {42, 43, 46})

    def test_without_repo_only_short_form(self):
        self.assertEqual(closing_refs("Closes aholt21754/job-search#42 and closes #46"), {46})
