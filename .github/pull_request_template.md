<!--
This repository is PUBLIC: no personal details in this description.

Task PR (normal case): "Closes #<task>". One task per PR.
Spec-only PR:          "Refs #<feature>" (never "Closes" a feature here).
Last task of a feature: also "Closes #<feature>", and set the feature's row in docs/BACKLOG.md to Done
                        with this PR's number in the PR column.
-->
Closes #<task>

**Feature:** #<feature>
**Spec:** docs/specs/NNN-title.md
**ADRs:** none

## Summary

## Acceptance criteria verified
- [ ] ...

## Checklist
- [ ] The spec matches what was built (discovered tasks added to the spec and on GitHub)
- [ ] Last task only: the backlog row is set to Done with this PR's number, and `Closes #<feature>` is above
- [ ] An ADR is added for any significant decision
- [ ] New ADRs are in `docs/adr/README.md`, and README summaries still match
- [ ] Tests, `check_backlog.py --github` and `check_personal_data.py` pass
- [ ] No personal details in the code, commit messages or this description
