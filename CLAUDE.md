# CLAUDE.md

## Project
A job-search assistant. The tech stack is not chosen yet (see `docs/BACKLOG.md`). **This repository is public.**

## Data & secrets (read first)
Full rules: `docs/adr/0003-personal-data-outside-repo.md`.
- Real personal data (resumes, cover letters, contacts, application notes, salary or offer details) lives in `JOB_SEARCH_DATA_DIR` (default `~/job-search-data`), **never inside the repo**.
- No personal details or credentials in files, commit messages, issues or PR text. All of them are public.
- Tests use made-up data only, under `tests/fixtures/`.
- Configuration comes from environment variables. `.env` is gitignored; `.env.example` documents the variables without values.
- Run `git config core.hooksPath scripts/hooks` once per clone. The pre-commit hook blocks personal-data files.

## Workflow
Full rules and reasoning: `docs/adr/0002-spec-driven-workflow-with-github-issues.md`.

**Feature issue + backlog row → spec (approved) → task issues → one PR per task → feature Done**

| Artifact | Source of truth for |
|---|---|
| `docs/specs/NNN-*.md` | Requirements, design, and **the list of tasks** |
| `docs/BACKLOG.md` | Features only: priority order and status |
| GitHub task issues | Task status and timing (opened, started, closed) |
| `docs/adr/` | Architectural decisions |

- **Feature:** a GitHub issue labelled `feature`. Its number is the backlog ID and names the spec (`docs/specs/042-title.md`).
  Statuses: `Proposed` → `Specced` → `In Progress` → `Done`, or `Dropped`.
- **Task:** a GitHub issue labelled `task`, a **sub-issue** of its feature, **about a day of work or less**, delivered by **exactly one PR**, squash-merged.
  Task issues are created when the spec is approved. A task found later gets the extra label `discovered`.
- **Status labels:** `status:proposed`, `status:specced`, `status:in-progress`. Done and Dropped are shown by closing the issue (as *completed* or *not planned*).
- **Start the clock:** add `status:in-progress` to a task **before** writing any code. Cycle time runs from then until the task closes.
- **Closing rules:**
  - A task PR says `Closes #<task>`.
  - A spec-only PR says `Refs #<feature>`, never `Closes`.
  - Only the PR for a feature's **last** task also says `Closes #<feature>`, sets the backlog row to `Done`, and puts its own PR number in the row.
    The number only exists once the PR is open, so push it in a follow-up commit. CI goes green after that push.
- **Never close an issue by hand**, except to drop it: comment the reason, close it as "not planned", drop the feature's open tasks too,
  and set the row to `Dropped` in a `docs/` PR.
- Don't start work that isn't in the backlog. A new request becomes a `Proposed` feature first.
- If the implementation diverges from the spec, update the spec first.

| Step | Slash command |
|---|---|
| New feature | `/new-backlog-item` |
| Write the spec, then create its tasks on approval | `/new-spec <feature>` |
| Add a discovered task | `/new-task <feature> <description>` |
| Start a task (label + branch) | `/start-task <task>` |
| Report the data | `/report` |
| Check for drift between GitHub and the files | `/sync-backlog` |
| Record a decision | `/new-adr <title>` |

Branches: `spec/42-short-title` for spec PRs, `task/57-short-title` for task PRs, `docs/42-short-title` for other
docs-only PRs (a new backlog row, a discovered task's spec line, dropping a feature). Those say `Refs #<feature>`. Never push to `main`.

## Development
**Testing**
- Write the test first and watch it fail, then write the code.
- Tests never call the network or the real GitHub. Use `tests/fakes.py`.
- Tests live in `tests/`. Run one with `python -m unittest tests.test_metrics.ThroughputTest.test_dst_boundary`.

**Commits and PRs**
- One task per PR, and keep it small.
- Commit message prefixes: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`. Put `#<task>` in the body.
- PR descriptions follow `.github/pull_request_template.md`.

**Dependencies**
- Standard library first. Adding a library or an external service needs an ADR.

**ADRs** (`/new-adr`)
- Write one for any decision that is hard to reverse or affects more than one feature: stack, libraries, storage, external APIs, auth, dropping a requirement. If unsure, ask.
- **Accepted ADRs are immutable.** To change a decision, write a new ADR and set the old one's status to `Superseded by ADR-NNNN`. CI enforces this.

## Commands
- Tests: `python -m unittest discover -s tests -t . -v`
- Workflow checks: `python scripts/check_backlog.py` (add `--github` to compare specs and backlog with GitHub)
- Personal-data check: `python scripts/check_personal_data.py` (add `--staged` for staged files only)
- Report: `python scripts/report.py [--feature N] [--since YYYY-MM-DD] [--csv PATH]`. Write the CSV **outside** the repo.
- Labels (one-off): `scripts/setup-labels.sh aholt21754/job-search`
- Build / lint / format: _TBD. Choosing the stack is a backlog feature, recorded as ADR-0004._

## README
- **Summaries only.** Each section is about 6 lines or fewer (the diagram doesn't count) and links to the detail in `docs/`.
- Never add detail or a list of ADRs; "Decisions" links to `docs/adr/`. CI limits: `README.md` 120 lines, `CLAUDE.md` 150.

## Gotchas
- **`gh pr create`, `gh repo view` and other GraphQL-based `gh` commands fail in Claude Code cloud sessions.** Use REST calls instead:
  - open a PR: `gh api repos/aholt21754/job-search/pulls -f title=... -f head=... -f base=main -F body=@file`;
  - create an issue: `gh api repos/aholt21754/job-search/issues -f title=... -F body=@file -f 'labels[]=task'`.
- **Adding a sub-issue needs the task's numeric `id`, not its number:**
  `gh api -X POST repos/aholt21754/job-search/issues/<feature>/sub_issues -F sub_issue_id=$(gh api repos/aholt21754/job-search/issues/<task> --jq .id)`
- **The personal-data check is deliberately strict.** It blocks any `.csv`, `.pdf` or other document file, any `data/` folder, and names containing resume, CV or cover letter. Made-up data goes in `tests/fixtures/`.
- **`report.py --since` only changes the weekly section.** The other sections cover all time.

## Definition of done (every PR)
- [ ] The PR says `Closes #<task>` (or `Refs #<feature>` for a spec-only PR) and links the spec
- [ ] The spec matches what was built, and any discovered task is in the spec and on GitHub
- [ ] On the feature's last task: the backlog row is `Done` with this PR's number, and the PR also says `Closes #<feature>`
- [ ] An ADR is written for any significant decision; `docs/adr/README.md` lists it, and README summaries still match (workflow, setup, data handling)
- [ ] Tests, `check_backlog.py --github` and `check_personal_data.py` all pass
- [ ] No personal details in the code, commit messages or PR text
