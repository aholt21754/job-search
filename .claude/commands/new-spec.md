---
description: Write the spec for a feature; on approval create its task sub-issues and move it to Specced
argument-hint: <feature issue number>
---
Write the spec for feature #$ARGUMENTS.

Rules: CLAUDE.md, `.claude/rules/specs.md` and ADR-0002. **Specs and issues are public: no personal details, made-up examples only.**

1. Read the issue (`gh api repos/aholt21754/job-search/issues/$ARGUMENTS`) and its row in `docs/BACKLOG.md`. If either is missing, stop and offer `/new-backlog-item`.
2. Ask clarifying questions one at a time, until the requirements, scope and acceptance criteria are clear.
3. Draft `docs/specs/<NNN>-<short-title>.md` from `docs/specs/_TEMPLATE.md`, with `Issue: #<feature>`.
   - Break the work into **tasks of about a day or less, one PR each**. Under `## Tasks`, list them as `- #TBD <description>` for now.
   - If the design makes a decision that is hard to reverse or affects more than one feature, draft an ADR (`/new-adr`).
4. **Show the user the spec and the task breakdown, and get explicit approval.** Don't create issues or write code before then.
5. **On approval**, for each task:
   - Create the issue: `gh api repos/aholt21754/job-search/issues -f title="<task>" -F body=@<file> -f 'labels[]=task' --jq '.number,.id'`. Base the body on `.github/ISSUE_TEMPLATE/task.md`, and write the file outside the repo.
   - Add it as a sub-issue: `gh api -X POST repos/aholt21754/job-search/issues/<feature>/sub_issues -F sub_issue_id=<id>`.
   - Replace its `#TBD` line in the spec with `- #<number> <description>`.
6. On branch `spec/<feature>-<short-title>`:
   - Set the backlog row to `Specced` with `[spec](specs/NNN-title.md)`.
   - Run `python scripts/check_backlog.py --github` and `python scripts/check_personal_data.py`.
   - Commit, push, and open the spec PR over REST, with `Refs #<feature>` in the body, **never `Closes`**.
7. **After the spec PR merges**, update the feature issue:
   - point its body's Spec link at `https://github.com/aholt21754/job-search/blob/main/docs/specs/NNN-title.md` (`gh api -X PATCH repos/aholt21754/job-search/issues/<feature> -F body=@<file>`);
   - swap the status label: `gh api -X DELETE repos/aholt21754/job-search/issues/<feature>/labels/status%3Aproposed`, then
     `gh api repos/aholt21754/job-search/issues/<feature>/labels -f 'labels[]=status:specced'`.
