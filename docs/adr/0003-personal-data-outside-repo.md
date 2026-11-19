# ADR-0003: Personal data stays outside the repository

- **Date:** 2026-11-17
- **Status:** Accepted
- **Related:** ADR-0002

## Context
This is a job-search project, so it will handle resumes, cover letters, contact names, application notes and possibly salary or offer details. **The repository is public.** Anything committed is visible to anyone and can be copied or indexed before it is noticed. Rewriting git history afterwards doesn't remove copies that have already been made. Issues, PR descriptions and commit messages are public too.

GitHub's secret scanning and push protection catch credentials, but not personal documents.

## Decision
We will:
1. **Keep real personal data outside the repository folder.** The app reads the location from the `JOB_SEARCH_DATA_DIR` environment variable, defaulting to `~/job-search-data`. Code must refuse a data folder that is inside the repository.
2. **Never put personal details in commits, issues, PR descriptions or commit messages.**
3. **Use made-up data in tests**, under `tests/fixtures/`, the only place document file types are allowed.
4. **Read configuration from environment variables.** `.env` files are gitignored, and `.env.example` documents the variables without values.
5. **Back these rules up with tooling:**
   - `.gitignore` patterns for document and spreadsheet types, `data/` and `job-search-data/` folders, and `.env*`;
   - `scripts/check_personal_data.py`, which blocks the same file types plus resume, CV and cover-letter file names. It runs as a **pre-commit hook** (`git config core.hooksPath scripts/hooks`, once per clone) and in **CI**.
6. **If personal data or a credential is pushed:** remove it, rotate any exposed credential straight away, and treat the content as permanently public. Report it privately (see `SECURITY.md`) rather than in a public issue.

## Alternatives Considered
- **Make the repository private:** the strongest protection. It was rejected because the project is intended to be public, and a private repo loses the free unlimited GitHub Actions minutes.
- **Keep data in a gitignored folder inside the repo:** one `git add -f` or a changed ignore rule exposes it. Keeping it outside the folder removes that failure mode.
- **Encrypt data in the repo (git-crypt and similar):** adds key management, and a misconfiguration publishes plaintext.
- **Rely on CI only:** CI runs after a push, and a pushed branch is already public. That's why the pre-commit hook matters.

## Consequences
- **Positive:** the most likely leak, an accidental commit, is stopped before it leaves the machine, and CI catches anyone who skipped the hook.
- **Negative:**
  - The check is deliberately strict. A legitimate `.csv`, a `data/` folder or a file named like `cv_*` must go under `tests/fixtures/` or be renamed.
  - The hook must be enabled in each clone.
- **Follow-ups:** when the app is built, its config loader enforces rule 1, and `.env.example` lists `JOB_SEARCH_DATA_DIR`.
