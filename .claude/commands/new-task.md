---
description: Add a task discovered after the spec was approved
argument-hint: <feature issue number> <task description>
---
Add a **discovered** task to a feature: $ARGUMENTS (the first word is the feature number).

Rules: CLAUDE.md and `.claude/rules/specs.md`. **Issues are public: no personal details.**

1. Check the size rule: about a day of work or less, in one PR. If it's bigger, propose a split into several tasks and confirm with the user.
2. Create the issue over REST, with labels `task` **and** `discovered`:
   `gh api repos/aholt21754/job-search/issues -f title="<task>" -F body=@<file> -f 'labels[]=task' -f 'labels[]=discovered' --jq '.number,.id'`
   Base the body on `.github/ISSUE_TEMPLATE/task.md`, and write the file outside the repo.
3. Add it as a sub-issue of the feature: `gh api -X POST repos/aholt21754/job-search/issues/<feature>/sub_issues -F sub_issue_id=<id>`.
4. Add `- #<number> <description>` to the feature spec's `## Tasks` section **in its own small PR** (branch `docs/<feature>-add-task-<number>`, body `Refs #<feature>`), and **merge it straight away**.
   Until it merges, the sub-issue exists on GitHub but not in `main`'s spec, so CI on other open PRs reports
   `#<number>: sub-issue of #<feature> but missing from spec`. Re-run their checks after the merge.
5. Run `python scripts/check_backlog.py --github`. Report the new issue's URL.
