"""Parse the repository's workflow documents. No network access."""
from __future__ import annotations

import re
from dataclasses import dataclass

STATUSES = {"Proposed", "Specced", "In Progress", "Done", "Dropped"}
NEEDS_SPEC = {"Specced", "In Progress", "Done"}
EMPTY = {"", "-", "—", "–"}

_CLOSING_RE = re.compile(
    r"(?<![\w/])(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+"
    r"(?:#|(?P<slug>[\w.-]+/[\w.-]+)#|https?://github\.com/(?P<url>[\w.-]+/[\w.-]+)/issues/)(?P<n>\d+)\b",
    re.I)
_LINK_RE = re.compile(r"^\[[^\]]*\]\(([^)]+)\)$")
_TASK_LINE_RE = re.compile(r"^- #(\d+)\s+(\S.*)$")
_STATUS_LINE_RE = re.compile(r"^\s*-?\s*\*\*Status:\*\*\s*(.+?)\s*$", re.M)


@dataclass
class Row:
    issue: int
    title: str
    status: str
    spec: str
    pr: str
    adrs: str
    line: int


@dataclass(frozen=True)
class SpecTask:
    number: int
    description: str


def parse_backlog(text: str, label: str) -> tuple[dict[int, Row], list[str]]:
    """Parse the backlog table. Returns rows keyed by issue number, and errors."""
    # Drop comments together with their trailing newline, so a comment between rows doesn't end the table.
    text = re.sub(r"<!--.*?-->[ \t]*\n?", "", text, flags=re.S)
    rows: dict[int, Row] = {}
    errors: list[str] = []
    in_table = False
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not in_table:
            in_table = bool(cells) and cells[0].lower() == "issue"
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue  # separator row
        if len(cells) != 6:
            errors.append(f"{label}:{n}: expected 6 columns (Issue|Title|Status|Spec|PR|ADRs), got {len(cells)}")
            continue
        m = re.fullmatch(r"#(\d+)", cells[0])
        if not m:
            errors.append(f"{label}:{n}: Issue must look like '#42', got {cells[0]!r}")
            continue
        issue = int(m.group(1))
        if issue in rows:
            errors.append(f"{label}:{n}: duplicate row for #{issue}")
        rows[issue] = Row(issue, cells[1], cells[2], cells[3], cells[4], cells[5], n)
    return rows, errors


def spec_link_target(cell: str) -> str | None:
    m = _LINK_RE.match(cell)
    return m.group(1) if m else None


def spec_issue(text: str) -> int | None:
    m = re.search(r"^Issue:\s*#(\d+)\b", text, re.M)
    return int(m.group(1)) if m else None


def parse_spec_tasks(text: str) -> tuple[list[SpecTask], list[str]]:
    """Read `- #N description` lines under `## Tasks`, up to the next `## ` heading.

    Prose lines are ignored; every list item must be a task line.
    """
    tasks: list[SpecTask] = []
    errors: list[str] = []
    in_tasks = False
    seen: set[int] = set()
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            in_tasks = line[3:].strip().lower() == "tasks"
            continue
        if not in_tasks or not line.lstrip().startswith(("-", "*")):
            continue
        m = _TASK_LINE_RE.match(line.strip())
        if not m:
            errors.append(f"task line {line.strip()!r} must look like '- #N description'")
            continue
        number = int(m.group(1))
        if number in seen:
            errors.append(f"task #{number} is listed more than once")
            continue
        seen.add(number)
        tasks.append(SpecTask(number, m.group(2).strip()))
    return tasks, errors


def adr_status(text: str) -> str | None:
    m = _STATUS_LINE_RE.search(text)
    return m.group(1) if m else None


def strip_adr_status(text: str) -> str:
    return _STATUS_LINE_RE.sub("", text).strip()


def closing_refs(body: str | None, repo: str | None = None) -> set[int]:
    """Issue numbers a PR body closes in this repo (close/fix/resolve keywords).

    `#N` always counts. `owner/repo#N` and issue URLs count only when they name `repo`.
    """
    refs = set()
    for m in _CLOSING_RE.finditer(body or ""):
        slug = m.group("slug") or m.group("url")
        if slug is None or (repo is not None and slug.lower() == repo.lower()):
            refs.add(int(m.group("n")))
    return refs
