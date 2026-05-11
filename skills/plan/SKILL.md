---
name: plan
description: Convert a user request into a concrete engineering plan and update harness state before implementation.
---

# /plan

## Goal
Turn a request into a scoped, verifiable plan recorded in `current-task.md` and `.harness/session-state.json`.

## Trigger
Use when the user says `/plan`, asks for a plan, or requests non-trivial work that should be tracked across sessions.

## Rules
- Read `/start` context first if not already done in this session.
- Keep the plan specific to the requested task.
- Do not include unrelated refactors.
- Define validation before implementation.
- Record open questions only when they block safe execution.

## Steps
1. Summarize the user request as a goal.
2. Identify scope, out-of-scope items, relevant files, and risks.
3. Choose validation commands from `docs/verification.md`.
4. Write a short step-by-step plan.
5. Update `current-task.md`.
6. Update `.harness/session-state.json` with status, phase, plan, next steps, and changed files if known.
7. Optionally add durable design choices to `docs/decisions.md`.

## Output Format
- Goal
- Scope
- Plan
- Validation commands
- Risks or assumptions
- Ready-to-implement status

## Completion Criteria
The task has a clear boundary, a recorded plan, acceptance criteria, and verification commands.
