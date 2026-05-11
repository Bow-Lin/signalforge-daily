---
name: review
description: Review current uncommitted changes for blockers, regressions, missing tests, and harness compliance.
---

# /review

## Goal
Inspect the current diff and report actionable risks before commit or handoff.

## Trigger
Use when the user says `/review`, before committing, or when a session has made meaningful changes.

## Rules
- Use code-review priority: bugs, regressions, safety risks, missing verification, and maintainability issues first.
- Do not stage, commit, or rewrite history.
- Include file and line references when possible.
- Separate findings by severity: BLOCKER, MAJOR, MINOR, QUESTION.
- If no issues are found, say so and identify residual test gaps.

## Steps
1. Run `git status --short --branch`.
2. Inspect `git diff` for tracked changes.
3. Inspect relevant untracked files with `git ls-files --others --exclude-standard`.
4. Compare changes against `current-task.md` scope.
5. Check whether validation has been run or documented.
6. Output findings.

## Output Format
- BLOCKER findings
- MAJOR findings
- MINOR findings
- QUESTION items
- Verification status
- Summary

## Completion Criteria
The user knows whether changes are safe to proceed, what must be fixed, and what verification evidence exists.
