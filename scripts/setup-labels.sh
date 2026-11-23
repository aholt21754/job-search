#!/usr/bin/env bash
# Create or update the labels used by the feature/task workflow (ADR-0002). Safe to run more than once.
# Uses the REST API only (GraphQL-based gh commands fail in Claude Code cloud sessions).
# Usage: scripts/setup-labels.sh owner/repo
set -euo pipefail
repo="${1:?usage: scripts/setup-labels.sh owner/repo}"

label() {  # name color description
  local encoded="${1//:/%3A}"
  if gh api "repos/$repo/labels/$encoded" --silent 2>/dev/null; then
    gh api -X PATCH "repos/$repo/labels/$encoded" -f color="$2" -f description="$3" --silent
    echo "updated $1"
  else
    gh api -X POST "repos/$repo/labels" -f name="$1" -f color="$2" -f description="$3" --silent
    echo "created $1"
  fi
}

label "feature"            "5319e7" "Backlog feature (row in docs/BACKLOG.md)"
label "task"               "1d76db" "About a day of work, one PR; sub-issue of a feature"
label "discovered"         "d93f0b" "Task added after the spec was approved"
label "status:proposed"    "c5def5" "Feature: proposed, no spec yet"
label "status:specced"     "0e8a16" "Feature: spec approved and merged"
label "status:in-progress" "fbca04" "Work underway (starts the cycle-time clock on tasks)"
# Deprecated label: only re-describe it if it exists.
if gh api "repos/$repo/labels/backlog" --silent 2>/dev/null; then
  gh api -X PATCH "repos/$repo/labels/backlog" -f description="Deprecated: replaced by feature/task" --silent
  echo "updated backlog (deprecated)"
fi
