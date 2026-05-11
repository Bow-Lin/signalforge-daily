---
name: start
description: Restore project harness context at the beginning of a new session and produce a Session Briefing without modifying code.
---

# /start

## Goal
Recover the current task, state, risks, verification expectations, and handoff point before any engineering work begins.

## Trigger
Use when the user says `/start`, starts a new session, asks for project status, or asks the agent to continue prior work.

## Rules
- Do not modify code or state files during `/start`.
- Read harness files before reading broad source code.
- Treat project files as the source of truth over chat history.
- If state files are missing or inconsistent, report that as a harness issue.

## Steps
1. Read `AGENTS.md`.
2. Read `current-task.md`.
3. Read `.harness/session-state.json`.
4. Read `.harness/session-log.md`.
5. Read `docs/decisions.md`.
6. Read `docs/error-journal.md`.
7. Skim `docs/architecture.md`, `docs/verification.md`, and `docs/coding-guidelines.md` as needed.
8. Run `git status --short --branch`.
9. Output a Session Briefing.

## Output Format
- Current goal
- Current status and phase
- Next 3 steps
- Changed or dirty files
- Known risks and blockers
- Required verification
- Recommended next action

## Completion Criteria
The user and agent can answer what the project is doing, where to resume, what risks exist, and how completion will be verified.
