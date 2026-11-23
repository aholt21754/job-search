---
paths:
  - "docs/specs/**"
---
# Spec rules

Full rules: `docs/adr/0002-spec-driven-workflow-with-github-issues.md`. Start new specs from `docs/specs/_TEMPLATE.md`.

- **File name:** `docs/specs/NNN-short-title.md`, where NNN is the **feature issue number**, zero-padded to 3 digits. The first line under the title is `Issue: #NNN`.
- **Requirements:** numbered and testable, written as "WHEN … THEN the system SHALL …".
- **`## Tasks`:** one line per task, in exactly this form: `- #<task issue> <one-line description>`.
  - No checkboxes and no status: task status lives on GitHub.
  - Each task is about a day of work or less, done in one PR. Split anything bigger before creating it.
  - The list must match the feature's GitHub sub-issues exactly. CI checks this.
- **Task issues are created when the user approves the spec** (`/new-spec`), and added as sub-issues of the feature.
- **A task discovered later** is added with `/new-task`: a GitHub issue labelled `task` and `discovered`, a sub-issue, and a line here. It follows the same size rule.
- **Specs are public.** No personal data, and use made-up examples.
- If the implementation must diverge from the spec, update the spec first.
