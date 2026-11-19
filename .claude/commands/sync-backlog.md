---
description: Report (and optionally fix) drift between BACKLOG.md, specs and GitHub issues
---
Check that `docs/BACKLOG.md`, `docs/specs/` and GitHub agree.

1. Run `python scripts/check_backlog.py --github`. It checks that spec task lists match sub-issues, and the `feature`/`task` type labels. Then run `python scripts/report.py`, and note its Audit section.
2. Fetch the features over REST: `gh api "repos/aholt21754/job-search/issues?labels=feature&state=all&per_page=100" --paginate`. Then compare each one with its backlog row:

   | Backlog status | Issue should be |
   |---|---|
   | Proposed | open, `status:proposed` |
   | Specced | open, `status:specced` |
   | In Progress | open, `status:in-progress` |
   | Done | closed as completed |
   | Dropped | closed as not planned |

   Also report `feature` issues with no row, and rows with no issue.
3. Check tasks (`labels=task`):
   - every task is a sub-issue of a feature;
   - an open task labelled `status:in-progress` belongs to a feature that is `In Progress`.
     (Closed tasks keep their labels. That's expected, not drift; never remove labels from closed tasks.)
   - a Dropped feature has no open tasks.
4. Show the findings as one table, then **ask before fixing anything**. The spec and the backlog are the source of truth, so fixes normally go to GitHub, not to the files.
