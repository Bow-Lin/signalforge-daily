#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "AGENTS.md"
  "current-task.md"
  "docs/architecture.md"
  "docs/verification.md"
  "docs/coding-guidelines.md"
  "docs/decisions.md"
  "docs/error-journal.md"
  ".harness/session-state.json"
  ".harness/session-log.md"
  ".harness/progress-map.md"
  ".harness/command-history.md"
  "skills/start/SKILL.md"
  "skills/plan/SKILL.md"
  "skills/review/SKILL.md"
  "skills/commit/SKILL.md"
  "skills/handoff/SKILL.md"
  "scripts/harness_check.sh"
  "scripts/safe_bash_guard.sh"
)

missing=0
for path in "${required_files[@]}"; do
  if [[ ! -f "${path}" ]]; then
    echo "MISSING ${path}"
    missing=1
  fi
done

if [[ "${missing}" -ne 0 ]]; then
  echo "Harness check failed"
  exit 1
fi

echo "Harness check passed"
