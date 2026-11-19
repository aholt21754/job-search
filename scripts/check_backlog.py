#!/usr/bin/env python3
"""Check docs/BACKLOG.md, docs/specs/ and docs/adr/ against the rules in CLAUDE.md and ADR-0002.

Local use (offline checks only):
    python scripts/check_backlog.py

Pull request mode (CI): also checks Done transitions, closing keywords and ADR immutability:
    PR_BODY="..." python scripts/check_backlog.py --base-ref origin/main --pr-number 12

Standard library only. Exits 1 if any errors are found.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workflow.docs import (  # noqa: E402
    EMPTY, NEEDS_SPEC, STATUSES, Row, adr_status, closing_refs, parse_backlog,
    parse_spec_tasks, spec_issue, spec_link_target, strip_adr_status,
)

ROOT = Path(__file__).resolve().parent.parent
DOC_LIMITS = {"README.md": 120, "CLAUDE.md": 150}
ADR_STATUS_RE = re.compile(r"^(Proposed|Accepted|Deprecated|Superseded by ADR-\d{4})$")


def _git_show(root: Path, ref: str, rel: str) -> str | None:
    res = subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=root, capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else None


def _check_rows(root: Path, rows: dict[int, Row]) -> list[str]:
    errors: list[str] = []
    docs = root / "docs"
    for r in rows.values():
        where = f"docs/BACKLOG.md:{r.line} (#{r.issue})"
        if r.status not in STATUSES:
            errors.append(f"{where}: invalid status {r.status!r}; use one of {sorted(STATUSES)}")
            continue
        if r.status == "Done" and not re.fullmatch(r"#\d+", r.pr):
            errors.append(f"{where}: Done rows need the PR number in the PR column (e.g. #57)")
        if r.spec in EMPTY:
            if r.status in NEEDS_SPEC:
                errors.append(f"{where}: status {r.status} requires a spec link")
            continue
        target = spec_link_target(r.spec)
        if not target:
            errors.append(f"{where}: Spec must be a markdown link like [spec](specs/042-title.md)")
            continue
        path = (docs / target).resolve()
        rel = f"docs/{target}"
        m = re.match(r"(\d+)-", path.name)
        if not path.is_file():
            errors.append(f"{where}: spec file not found: {rel}")
            continue
        if not m or int(m.group(1)) != r.issue:
            errors.append(f"{where}: spec filename {path.name} must start with the issue number ({r.issue:03d}-)")
            continue
        text = path.read_text(encoding="utf-8")
        if spec_issue(text) != r.issue:
            errors.append(f"{rel}: missing 'Issue: #{r.issue}' line")
        tasks, task_errors = parse_spec_tasks(text)
        errors.extend(f"{rel}: {e}" for e in task_errors)
        if r.status in NEEDS_SPEC and not tasks and not task_errors:
            errors.append(f"{rel}: no tasks listed under ## Tasks")
    return errors


def _check_spec_files(root: Path, rows: dict[int, Row]) -> list[str]:
    errors: list[str] = []
    for path in sorted((root / "docs" / "specs").glob("*.md")):
        if path.name.startswith("_"):
            continue
        m = re.match(r"(\d+)-[\w.-]+\.md$", path.name)
        if not m:
            errors.append(f"docs/specs/{path.name}: name must be NNN-short-title.md (NNN = feature issue number)")
        elif int(m.group(1)) not in rows:
            errors.append(f"docs/specs/{path.name}: no backlog row for #{int(m.group(1))}")
    return errors


def _check_adr_files(root: Path) -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}
    for path in sorted((root / "docs" / "adr").glob("*.md")):
        if path.name.startswith("_") or path.name == "README.md":
            continue
        m = re.match(r"(\d{4})-[\w.-]+\.md$", path.name)
        if not m:
            errors.append(f"docs/adr/{path.name}: name must be NNNN-short-title.md")
            continue
        if m.group(1) in seen:
            errors.append(f"docs/adr/{path.name}: number {m.group(1)} already used by {seen[m.group(1)]}")
        seen[m.group(1)] = path.name
        status = adr_status(path.read_text(encoding="utf-8"))
        if status is None or not ADR_STATUS_RE.match(status):
            errors.append(f"docs/adr/{path.name}: Status must be Proposed, Accepted, Deprecated or "
                          f"'Superseded by ADR-NNNN' (got {status!r})")
    return errors


def _check_doc_limits(root: Path) -> list[str]:
    errors = []
    for name, limit in DOC_LIMITS.items():
        path = root / name
        if not path.is_file():
            continue
        count = len(path.read_text(encoding="utf-8").splitlines())
        if count > limit:
            errors.append(f"{name}: {count} lines; the limit is {limit} "
                          f"(summaries only; move detail into docs/ and link to it)")
    return errors


def _check_adr_index(root: Path) -> list[str]:
    adr_dir = root / "docs" / "adr"
    adrs = sorted(p.name for p in adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md"))
    if not adrs:
        return []
    index = adr_dir / "README.md"
    if not index.is_file():
        return ["docs/adr/README.md not found: add an index listing every ADR"]
    text = index.read_text(encoding="utf-8")
    return [f"docs/adr/README.md: missing ADR {name}" for name in adrs if name not in text]


def _check_pr_offline(root: Path, rows: dict[int, Row], base_ref: str, pr_number: int, body: str,
                      check_closes: bool = True, repo: str | None = None) -> list[str]:
    errors: list[str] = []
    base_rows, _ = parse_backlog(_git_show(root, base_ref, "docs/BACKLOG.md") or "", f"{base_ref}:docs/BACKLOG.md")
    closes = closing_refs(body, repo)

    for r in rows.values():
        was = base_rows.get(r.issue)
        if r.status == "Done" and (was is None or was.status != "Done"):
            if r.issue not in closes:
                errors.append(f"#{r.issue} moves to Done, but the PR description has no 'Closes #{r.issue}'")
            if r.pr != f"#{pr_number}":
                errors.append(f"#{r.issue} moves to Done; its PR column should be #{pr_number} (got {r.pr!r})")

    for n in sorted(closes) if check_closes else []:
        # With GitHub access, _check_pr_github applies the stricter version of this rule.
        if n in rows and rows[n].status != "Done":
            errors.append(f"PR says 'Closes #{n}' but the backlog row is {rows[n].status!r}. "
                          f"Use 'Refs #{n}' for spec-only PRs, or set the row to Done")

    errors += _check_adr_immutability(root, base_ref)
    return errors


def _base_adr_files(root: Path, base_ref: str) -> list[str]:
    res = subprocess.run(["git", "ls-tree", "--name-only", f"{base_ref}:docs/adr"], cwd=root,
                         capture_output=True, text=True)
    return [n for n in res.stdout.splitlines() if re.match(r"\d{4}-.*\.md$", n)] if res.returncode == 0 else []


def _check_adr_immutability(root: Path, base_ref: str) -> list[str]:
    """Accepted ADRs (as of the base) may not be deleted, renamed or edited.

    The only allowed change is the Status line moving to 'Superseded by ADR-NNNN' (or staying Accepted).
    """
    errors: list[str] = []
    for name in _base_adr_files(root, base_ref):
        rel = f"docs/adr/{name}"
        old = _git_show(root, base_ref, rel)
        if old is None or adr_status(old) != "Accepted":
            continue
        path = root / rel
        if not path.is_file():
            errors.append(f"{rel}: Accepted ADRs may not be deleted or renamed. Supersede it with a new ADR instead")
            continue
        new = path.read_text(encoding="utf-8")
        status = adr_status(new) or ""
        if status != "Accepted" and not re.fullmatch(r"Superseded by ADR-\d{4}", status):
            errors.append(f"{rel}: an Accepted ADR's status may only change to 'Superseded by ADR-NNNN' "
                          f"(got {status!r})")
        if strip_adr_status(old) != strip_adr_status(new):
            errors.append(f"{rel}: Accepted ADRs are immutable. Write a new ADR that supersedes it instead")
    return errors


def _labels(issue: dict) -> set[str]:
    return {lb["name"] for lb in issue.get("labels", [])}


def _spec_tasks_for(root: Path, row: Row) -> list[int] | None:
    """Task numbers listed in the row's spec, or None if the row has no readable spec."""
    target = spec_link_target(row.spec) if row.spec not in EMPTY else None
    path = (root / "docs" / target) if target else None
    if not path or not path.is_file():
        return None
    tasks, _ = parse_spec_tasks(path.read_text(encoding="utf-8"))
    return [t.number for t in tasks]


def _check_github(root: Path, rows: dict[int, Row], gh) -> list[str]:
    errors: list[str] = []
    for r in rows.values():
        try:
            feature = gh.issue(r.issue)
        except RuntimeError as e:
            errors.append(f"#{r.issue}: cannot read the feature issue ({e})")
            continue
        if "feature" not in _labels(feature):
            errors.append(f"#{r.issue}: backlog item is not labelled feature on GitHub")
        listed = _spec_tasks_for(root, r)
        if listed is None:
            continue
        subs = {i["number"]: i for i in gh.sub_issues(r.issue)}
        for n in listed:
            if n not in subs:
                errors.append(f"#{n}: listed in the spec for #{r.issue} but not a sub-issue of #{r.issue}")
        for n in sorted(set(subs) - set(listed)):
            errors.append(f"#{n}: sub-issue of #{r.issue} but missing from spec")
        for n in listed:
            try:
                issue = subs.get(n) or gh.issue(n)
            except RuntimeError as e:
                errors.append(f"#{n}: cannot read task issue ({e})")
                continue
            if "task" not in _labels(issue):
                errors.append(f"#{n}: listed as a task of #{r.issue} but not labelled task")
    return errors


def _moving_to_done(root: Path, rows: dict[int, Row], base_ref: str) -> set[int]:
    base_rows, _ = parse_backlog(_git_show(root, base_ref, "docs/BACKLOG.md") or "", "base")
    return {n for n, r in rows.items()
            if r.status == "Done" and (n not in base_rows or base_rows[n].status != "Done")}


def _check_pr_github(root: Path, rows: dict[int, Row], gh, base_ref: str, body: str) -> list[str]:
    errors: list[str] = []
    closes = closing_refs(body, getattr(gh, "repo", None))
    done_now = _moving_to_done(root, rows, base_ref)
    for n in sorted(done_now):
        for task in gh.sub_issues(n):
            if task.get("state") != "closed" and task["number"] not in closes:
                errors.append(f"#{n} moves to Done but task #{task['number']} is still open "
                              f"and not closed by this PR")
    for n in sorted(closes):
        try:
            labels = _labels(gh.issue(n))
        except RuntimeError as e:
            errors.append(f"PR closes #{n}, which cannot be read ({e})")
            continue
        if "task" in labels or ("feature" in labels and n in done_now):
            continue
        errors.append(f"PR closes #{n}: a PR may only close task issues, or a feature whose backlog row "
                      f"moves to Done in the same PR. Use 'Refs #{n}' instead")
    return errors


def run_checks(root: Path, gh=None, base_ref: str | None = None, pr_number: int | None = None,
               pr_body: str | None = None) -> list[str]:
    """Run every check and return the error messages (empty list = pass)."""
    backlog = root / "docs" / "BACKLOG.md"
    if not backlog.is_file():
        return ["docs/BACKLOG.md not found"]
    rows, errors = parse_backlog(backlog.read_text(encoding="utf-8"), "docs/BACKLOG.md")
    errors += _check_rows(root, rows)
    errors += _check_spec_files(root, rows)
    errors += _check_adr_files(root)
    errors += _check_adr_index(root)
    errors += _check_doc_limits(root)
    if gh is not None:
        errors += _check_github(root, rows, gh)
    if base_ref is not None:
        errors += _check_pr_offline(root, rows, base_ref, pr_number or 0, pr_body or "",
                                    check_closes=gh is None, repo=getattr(gh, "repo", None))
        if gh is not None:
            errors += _check_pr_github(root, rows, gh, base_ref, pr_body or "")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-ref", help="git ref of the PR base (enables PR checks)")
    ap.add_argument("--pr-number", type=int, help="number of the PR being checked")
    ap.add_argument("--github", action="store_true", help="also check against GitHub (needs gh)")
    args = ap.parse_args(argv)
    if args.base_ref and args.pr_number is None:
        ap.error("--pr-number is required with --base-ref")

    gh = None
    if args.github:
        from workflow.github import GitHub, repo_slug
        gh = GitHub(repo_slug(ROOT))
    errors = run_checks(ROOT, gh, args.base_ref, args.pr_number, os.environ.get("PR_BODY", ""))
    if errors:
        print(f"Backlog check FAILED ({len(errors)} problem(s)):")
        for e in errors:
            print(f"  - {e}")
            if os.environ.get("GITHUB_ACTIONS"):
                print(f"::error::{e}")
        return 1
    rows, _ = parse_backlog((ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8"), "")
    print(f"Backlog check passed ({len(rows)} backlog row(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
