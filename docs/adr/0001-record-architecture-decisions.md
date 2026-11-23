# ADR-0001: Record architecture decisions

- **Date:** 2026-11-16
- **Status:** Accepted
- **Related:** —

## Context
Decisions about this project's architecture, tools and process need to be recorded along with the reasons for them, so that future contributors (people and AI assistants) can understand why things are the way they are and avoid reopening settled questions without new information.

## Decision
We will use Architecture Decision Records, as described by Michael Nygard, stored in `docs/adr/` as `NNNN-title.md` and based on `docs/adr/_TEMPLATE.md`. Accepted ADRs are immutable; a changed decision gets a new ADR that supersedes the old one.

## Alternatives Considered
- **Decisions in issue or PR comments:** hard to find later, and not versioned with the code.
- **A single DECISIONS.md:** turns into an edited-in-place log, losing history and context.

## Consequences
- **Positive:** a durable, reviewable record of why things are the way they are.
- **Negative:** a small overhead for each significant decision.
- **Follow-ups:** CLAUDE.md tells the AI assistant when ADRs are required.
