---
description: Start a task. Labels it in progress (starting the cycle-time clock) and creates its branch
argument-hint: <task issue number>
---
Start task #$ARGUMENTS.

Rules: CLAUDE.md (Workflow). **Do steps 1–2 before writing any code. The label starts the cycle-time clock.**

1. Read the task (`gh api repos/aholt21754/job-search/issues/$ARGUMENTS`). Check that it's open, labelled `task`, and listed in its feature's spec. Find the feature by looking for the spec line `- #$ARGUMENTS`.
2. Add the label: `gh api repos/aholt21754/job-search/issues/$ARGUMENTS/labels -f 'labels[]=status:in-progress'`.
3. Create the branch `task/$ARGUMENTS-<short-title>` from the latest `main`.
4. **If this is the feature's first task to start:**
   - add `status:in-progress` to the feature issue, and remove `status:specced` from it;
   - on this task branch, set the feature's backlog row to `In Progress`.
5. Summarise the task and its acceptance criteria from the spec, then begin with a failing test.
6. When it's done, open the PR over REST using `.github/pull_request_template.md`, with `Closes #$ARGUMENTS`. **If this is the feature's last open task**, also follow the Done rule in CLAUDE.md, in this order:
   commit the Done row with `#TBD` in the PR column, open the PR, then push one more commit that replaces `#TBD`
   with the PR number the API returned. The first CI run fails until that push; that's expected.
