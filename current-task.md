# Current Task

## Goal
Initialize a Standard Project Harness for this Python `news_collection` repository so future Codex or Claude Code sessions can restore context, follow project rules, verify work, record failures, and hand off cleanly.

## Current Status
Completed. Standard Harness files have been created for protocol, state, verification, skills, and safety boundaries. No business logic files were modified for this task.

## Scope
- Create harness documentation under `docs/`.
- Create structured state under `.harness/`.
- Create project skills under `skills/start`, `skills/plan`, `skills/review`, `skills/commit`, and `skills/handoff`.
- Create boundary scripts under `scripts/`.
- Update `AGENTS.md` as the harness protocol entry point.
- Adjust `.gitignore` so the external `skills/ai-daily-digest/` checkout stays ignored while project harness skills can be tracked.

## Relevant Files
- `AGENTS.md`
- `current-task.md`
- `docs/architecture.md`
- `docs/verification.md`
- `docs/coding-guidelines.md`
- `docs/decisions.md`
- `docs/error-journal.md`
- `.harness/session-state.json`
- `.harness/session-log.md`
- `.harness/progress-map.md`
- `.harness/command-history.md`
- `skills/*/SKILL.md`
- `scripts/harness_check.sh`
- `scripts/safe_bash_guard.sh`

## Plan
1. Inspect repository structure, tooling, tests, and git status.
2. Create the Standard Harness file set.
3. Write concise project-specific protocol, verification, state, and skill instructions.
4. Add boundary scripts for harness checks and dangerous command detection.
5. Run harness self-check or record why it cannot run.
6. Update state and session log with the initialization result.

## Validation Commands
- `uv run python -m pytest -q`
- `bash scripts/harness_check.sh` when a POSIX shell is available
- Equivalent PowerShell file-presence check when `bash`/`sh` are unavailable

## Acceptance Criteria
- New sessions can recover the active task from `current-task.md` and `.harness/session-state.json`.
- `AGENTS.md` points agents to the harness protocol and required reading order.
- `docs/verification.md` documents validation for code, docs, harness changes, and skipped checks.
- `/start`, `/plan`, `/review`, `/commit`, and `/handoff` skills exist with usable operating steps.
- `scripts/harness_check.sh` and `scripts/safe_bash_guard.sh` exist.
- Harness initialization does not modify `src/` business logic.

## Risks
- Current Windows environment has no `bash` or `sh`, so shell script execution may need to be verified later on a POSIX-capable environment.
- The repository already contains an ignored external skill checkout at `skills/ai-daily-digest/`; it must not be included accidentally.

## Next 3 Steps
1. Review the harness diff and commit it if the file set looks good.
2. In a POSIX-capable environment, run `bash scripts/harness_check.sh` and optionally `bash -n scripts/safe_bash_guard.sh`.
3. For the next engineering task, begin with `/start`, then use `/plan` before changing business code.

## Last Updated
2026-05-11T16:05:29+08:00
