#!/usr/bin/env python3
"""Block personal data from being committed to this public repository (ADR-0003).

    python scripts/check_personal_data.py           # every tracked file (CI)
    python scripts/check_personal_data.py --staged  # files staged for commit (pre-commit hook)

Made-up test data under tests/fixtures/ is allowed. Exits 1 if anything is blocked.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import PurePosixPath

ALLOWED_PREFIX = "tests/fixtures/"
BLOCKED_EXTENSIONS = {".pdf", ".doc", ".docx", ".odt", ".rtf", ".pages", ".xls", ".xlsx", ".csv"}
BLOCKED_DIRS = {"data", "job-search-data"}
# Word boundaries are any non-letter (so digits count: Resume2026, CV2026); CamelCase is split first.
_NAME_RE = re.compile(r"(?:^|[^a-zé])(résumés?|resumés?|resumes?|cvs?|cover[-_ ]?letters?)(?:[^a-zé]|$)")


def _looks_like_resume(part: str) -> bool:
    part = unicodedata.normalize("NFC", part)  # macOS file names arrive decomposed (e + combining accent)
    spaced = re.sub(r"([a-zé])([A-ZÉ])", r"\1 \2", part)
    return bool(_NAME_RE.search(spaced.lower()))


def find_violations(paths: list[str]) -> list[str]:
    violations = []
    for raw in paths:
        if raw.startswith(ALLOWED_PREFIX):
            continue
        p = PurePosixPath(raw)
        name = p.name.lower()
        if p.suffix.lower() in BLOCKED_EXTENSIONS:
            violations.append(f"{raw}: document/spreadsheet files ({p.suffix.lower()}) may hold personal data")
        elif any(part.lower() in BLOCKED_DIRS for part in p.parts[:-1]):
            violations.append(f"{raw}: data folders belong outside the repo (JOB_SEARCH_DATA_DIR)")
        elif name == ".env" or (name.startswith(".env.") and name != ".env.example"):
            violations.append(f"{raw}: environment files hold credentials; only .env.example may be committed")
        elif any(_looks_like_resume(part) for part in p.parts):
            violations.append(f"{raw}: looks like a resume, CV or cover letter")
    return violations


def _git_paths(staged: bool) -> list[str]:
    # -z: NUL-separated, unquoted paths. Without it git escapes non-ASCII names ("r\303\251sum\303\251.md")
    # and they would slip past every pattern.
    cmd = (["git", "diff", "--cached", "--name-only", "--diff-filter=ACR", "-z"] if staged
           else ["git", "ls-files", "-z"])
    out = subprocess.run(cmd, capture_output=True, check=True).stdout.decode("utf-8", errors="replace")
    return [path for path in out.split("\0") if path]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--staged", action="store_true", help="check only files staged for commit")
    args = ap.parse_args(argv)
    violations = find_violations(_git_paths(args.staged))
    if violations:
        print("Personal-data check FAILED. This repository is public; these files must not be committed:")
        for v in violations:
            print(f"  - {v}")
        print("Keep personal data in JOB_SEARCH_DATA_DIR (outside the repo). Test data goes in tests/fixtures/.")
        return 1
    print("Personal-data check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
