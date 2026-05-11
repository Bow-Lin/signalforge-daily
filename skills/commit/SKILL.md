---
name: commit
description: Run pre-commit review and verification, update harness logs, and prepare a commit message; do not commit unless explicitly asked.
---

# /commit

## Goal
Prepare changes for commit with review, verification evidence, and harness state updates.

## Trigger
Use when the user says `/commit`, asks whether changes are ready to commit, or asks to create a commit.

## Rules
- Unless the user explicitly asks to commit, stop after review, verification, and a proposed commit message.
- Never include unrelated user changes silently.
- Do not commit generated outputs from `paper/`, `blog/`, `output/`, `logs/`, caches, or virtual environments.
- Run relevant verification from `docs/verification.md`.
- Stop on BLOCKER or MAJOR review findings unless the user asks to proceed with known risk.

## Steps
1. Run `/review` workflow.
2. Identify intended files to include.
3. Run verification commands appropriate to the change.
4. Update `.harness/session-log.md` with verification results.
5. Update `.harness/session-state.json` with changed files and validation result.
6. Propose a concise imperative commit message.
7. If explicitly authorized, stage only intended files and run `git commit`.

## Output Format
- Intended files
- Review result
- Verification commands and results
- Proposed commit message
- Commit result, if a commit was requested

## Completion Criteria
Changes are reviewed, verification evidence is recorded, and either a commit is created by request or the user has a clear commit-ready summary.
