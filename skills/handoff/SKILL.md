---
name: handoff
description: Seal the session state so future agents can resume without relying on chat history.
---

# /handoff

## Goal
Record what happened, what changed, what was verified, what remains open, and exactly where the next session should resume.

## Trigger
Use when the user says `/handoff`, at the end of substantive work, before stopping for the day, or when context may be lost.

## Rules
- Update project files; do not rely on chat history.
- Record failed or skipped checks honestly.
- Add durable decisions to `docs/decisions.md`.
- Add recurring or non-obvious failures to `docs/error-journal.md`.
- Keep the handoff concise enough to scan quickly.

## Steps
1. Run `git status --short --branch`.
2. Summarize completed work and changed files.
3. Summarize verification commands and outcomes.
4. Update `current-task.md` status, next steps, risks, and last updated timestamp.
5. Update `.harness/session-state.json` status, phase, changed files, validation, and `handoff.resume_from`.
6. Append an entry to `.harness/session-log.md`.
7. Update `docs/decisions.md` or `docs/error-journal.md` if new durable knowledge exists.

## Output Format
- Completed
- Changed files
- Verification
- Open risks
- Resume from

## Completion Criteria
A new session can run `/start` and continue without needing the prior chat transcript.
