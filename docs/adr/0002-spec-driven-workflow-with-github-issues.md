# ADR-0002: Spec-driven workflow with features, task issues and cycle-time tracking

- **Date:** 2026-11-17
- **Status:** Accepted
- **Related:** ADR-0001

## Context
We want work to be **trackable and predictable**. Spec-sized tickets are too big and too uneven to forecast from. Small tickets of a consistent size give a steady stream of completed items, and that stream is the raw data for estimating. Estimation itself is out of scope here. This ADR makes sure the right data is **recorded consistently** and **reported**.

We also want a clear source of truth for what each feature must do (the spec, reviewed like code), a visible priority order, and a hard link between each unit of work and the change that delivered it.

## Decision

### Units of work
| Unit | Lives in | Size | Delivered by |
|---|---|---|---|
| **Feature** | A row in `docs/BACKLOG.md` + a GitHub issue labelled `feature` + one spec | Any | Several task PRs |
| **Task** | A GitHub issue labelled `task`, a **sub-issue** of its feature | About a day of work or less; split anything bigger before creating it | **Exactly one PR**, squash-merged, so one commit on `main` |

- The **feature issue number is the backlog ID**, and it names the spec: `docs/specs/042-short-title.md`.
- `docs/BACKLOG.md` lists **features only**, in priority order. Tasks are not listed there.

### Sources of truth
| What | Source of truth |
|---|---|
| Requirements, design, and the **list of tasks** | The spec |
| Feature priority and status | `docs/BACKLOG.md` |
| Task status and timing (opened, started, closed) | GitHub task issues |
| Architectural decisions | `docs/adr/` |

The spec's task list holds only an issue link and a one-line description per task (`- #57 Add login form`), never a status or checkbox. **CI checks that each spec's task list matches its feature issue's sub-issues exactly.**

### Labels
- **Type** (exactly one per issue): `feature`, `task`.
- **`discovered`**: on tasks only, for tasks created **after the spec was approved**. Planned tasks don't get it. This keeps scope growth measurable.
- **Status**: `status:proposed`, `status:specced`, `status:in-progress`. Done and Dropped are expressed by closing the issue (as *completed* or *not planned*), not by a label.

### Feature lifecycle
| Backlog status | Feature issue | How it gets there |
|---|---|---|
| Proposed | open, `status:proposed` | Issue created, then backlog row added |
| Specced | open, `status:specced` | Spec approved by the user and merged in a spec-only PR (`Refs #feature`). On approval, task issues are created as sub-issues and listed in the spec. |
| In Progress | open, `status:in-progress` | The first task starts. The row is updated in that task's PR. |
| Done | closed as completed | The PR for the **last open task** also says `Closes #feature`, sets the row to Done and fills in the PR column. |
| Dropped | closed as not planned | Comment the reason; close its open tasks as not planned too |

### Task lifecycle
| State | Task issue |
|---|---|
| To do | open, no status label |
| In progress | open, `status:in-progress`. **Adding this label starts the cycle-time clock.** |
| Done | closed as completed **by its PR** (`Closes #task`). **Closing stops the clock.** |
| Dropped | closed as not planned. Excluded from timing data. |

- **Discovered tasks** go through the same steps: create the issue (labels `task` and `discovered`), add it as a sub-issue, and add its line to the spec. All of this follows the same size rule.
- **Every task closed as completed must have a PR** that says `Closes #<task>`. CI makes sure a PR only closes task issues (or the feature it completes). The report's audit lists any completed task without a linked PR, which catches tasks closed by hand or PRs that forgot `Closes`.

### Branches and PRs
- Spec PR: branch `spec/42-short-title`, body says `Refs #42`.
- Task PR: branch `task/57-short-title`, body says `Closes #57` and links the feature (`Feature: #42`) and the spec.
- Squash merge is the merge method, so each task becomes one commit on `main`.

### CI enforcement (`scripts/check_backlog.py`, run by `.github/workflows/ci.yml`, job `checks`)
Offline checks (always):
- Backlog rows have valid IDs and statuses, and a spec link once Specced or later.
- Spec filenames match their feature number and contain `Issue: #N`. No orphan specs.
- Specced-or-later specs have a non-empty task list in `- #N description` form.
- ADR naming and statuses are valid, and Accepted ADRs aren't edited.

GitHub checks (in CI, or locally with `--github`, using `gh api` over REST):
- Each spec's task list matches its feature's sub-issues exactly, and every task has the `task` label.
- A row moving to Done needs `Closes #feature` in the PR body and this PR's number in the PR column. All of the feature's tasks must be closed, or be closed by this PR.
- `Closes #N` may only target a `task`, or a `feature` whose row moves to Done in this PR.

### Reporting (`scripts/report.py`)
Reports the data only. **No forecasts.**
- **Tasks finished per week:** tasks closed as completed, by ISO week (Monday start, US Eastern time: `America/New_York`), including weeks with zero.
- **Time per task (cycle time):** from when `status:in-progress` was **first** added to when the task closed. Shown per task and summarised (count, median, mean, min, max). Tasks that were never labelled in progress are listed, not guessed.
- **Discovered tasks:** planned vs discovered count, per feature and in total.
- **Remaining tasks:** open tasks per feature, split into to do and in progress.
- **Audit:** completed tasks with no linked PR, tasks with no parent feature, and completed tasks with no in-progress timestamp.
- **`--csv <path>`:** one row per task, for estimation outside the script. Columns: task, title, feature, discovered, state, state reason, created, first started, last started, closed, cycle time (days), PR.
- Filters: `--feature N`, and `--since YYYY-MM-DD`, which sets the first week shown in the weekly section; the other sections cover all time.

## Alternatives Considered
- **One issue per spec, with tasks as checkboxes in the spec** (this ADR's first draft): tickets are too big and uneven to forecast from.
- **Task list only on GitHub, not in the spec:** no drift, but the work breakdown isn't reviewed or versioned with the spec.
- **Checkboxes in the spec ticked by each task PR:** duplicates GitHub's status, and causes conflicts when tasks run in parallel.
- **Every task listed in `BACKLOG.md`:** the file grows long, and every task PR edits it, which causes conflicts.
- **Separate backlog IDs (F-001) alongside issue numbers:** two numbering schemes that drift apart.
- **Cycle time from created to closed:** includes time spent waiting in the queue, so it says little about how long work takes.
- **A `status:todo` label:** redundant, since an open task without `status:in-progress` is waiting.

## Consequences
- **Positive:**
  - Small, consistently sized tasks with reliable start and finish timestamps, and discovered work visibly separated from planned work.
  - The spec stays the reviewed record of what is being built.
  - CI catches drift between the spec and GitHub.
- **Negative:**
  - More issues to manage. The slash commands do most of this work.
  - CI needs GitHub API access. The default `GITHUB_TOKEN` with read permission is enough.
  - Timing data is only as good as the habit of adding `status:in-progress` when work starts.
  - Issue numbers have gaps because PRs share the counter, and moving off GitHub would mean renumbering.
- **Follow-ups:**
  - Labels: `feature`, `task`, `discovered`, `status:*`. `backlog` is no longer used.
  - Set the repo to squash merge only.
  - Slash commands for creating, starting and adding tasks, and for running the report.
  - Estimation is a separate future decision built on the report's data.
