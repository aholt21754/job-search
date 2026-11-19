---
description: Record an architecture decision as a new ADR
argument-hint: <decision title>
---
Create an ADR for: $ARGUMENTS

1. Find the next number: the highest `docs/adr/NNNN-*.md` plus 1.
2. Create `docs/adr/NNNN-<kebab-title>.md` from `docs/adr/_TEMPLATE.md`, dated today with Status `Proposed`.
3. Fill in Context, Decision ("We will…"), Alternatives Considered (with the reason each was rejected) and Consequences, using what you've discussed with the user. Ask about anything you'd otherwise be guessing.
4. If it replaces an earlier decision, set the old ADR's Status to `Superseded by ADR-NNNN`. Change nothing else in the old ADR.
5. Add a row for it to `docs/adr/README.md` (number, title, status). If it supersedes an ADR, update that ADR's status in the index too.
6. If the decision changes something the README summarises (the workflow, project setup, data handling), update that summary, keeping within the README rules in CLAUDE.md. Most ADRs don't need a README change.
7. Link the ADR from the related spec's Design section, the backlog row's ADRs column, and the issue body.
8. Ask the user to accept it, then set Status to `Accepted` in the ADR and in the index. Run `python scripts/check_backlog.py`.
