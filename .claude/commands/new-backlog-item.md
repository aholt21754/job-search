---
description: Create a feature issue on GitHub and its row in docs/BACKLOG.md
argument-hint: <short title and description>
---
Add a new backlog **feature** for: $ARGUMENTS

Rules: CLAUDE.md (Workflow) and ADR-0002. **Issues are public: no personal details.**

1. If the request is vague, ask up to 3 short questions so you can write a 1–3 sentence summary. Don't write requirements; they go in the spec.
2. Write the body to a temp file **outside the repo**, using `.github/ISSUE_TEMPLATE/feature.md` (Summary, `Spec: _pending_`, Related ADRs). Create the issue over REST:
   `gh api repos/aholt21754/job-search/issues -f title="<title>" -F body=@<file> -f 'labels[]=feature' -f 'labels[]=status:proposed' --jq .number`
3. Add a row to `docs/BACKLOG.md` for that number: Status `Proposed`, Spec/PR/ADRs `—`. Ask where it goes in the priority order if that isn't obvious.
4. Run `python scripts/check_backlog.py --github`. Commit on a branch and open a PR over REST (see CLAUDE.md Gotchas), with `Refs #<feature>` in its body.
5. Report the issue URL, and ask whether to write the spec now (`/new-spec <number>`).
