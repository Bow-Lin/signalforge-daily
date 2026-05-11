# Project Harness Protocol

## Agent Role
You are an engineering agent working in the `news_collection` repository. Your job is to make changes that are recoverable across sessions, verified by commands, and recorded in the project harness before handoff.

## Core Principle
Reliable project files carry state; chat history is not the source of truth. Before acting, restore context from the harness. Before claiming completion, run the relevant checks or record why they could not run.

## Required Reading Order
At the start of a new session, read:
1. `current-task.md`
2. `.harness/session-state.json`
3. `.harness/session-log.md`
4. `docs/decisions.md`
5. `docs/error-journal.md`
6. Relevant sections of `docs/architecture.md`, `docs/verification.md`, and `docs/coding-guidelines.md`

Then output a short Session Briefing before modifying files.

## Operating Rules
- Keep business logic in `src/news_collection/` and tests in `tests/`.
- Do not rely on generated output directories as source: `paper/`, `blog/`, `output/`, and `logs/` stay local.
- Do not commit secrets. `.env` is local only; API keys come from environment variables.
- Use `uv` as the preferred environment manager.
- Preserve user changes that are outside the requested scope.

## Planning Rules
- For non-trivial changes, update `current-task.md` and `.harness/session-state.json` with goal, scope, plan, risks, and next steps.
- Keep plans small enough to verify in one session.
- Record durable design choices in `docs/decisions.md`.

## Verification Policy
- Follow `docs/verification.md` for command selection.
- Normal Python changes should run `uv run python -m pytest -q` unless the change is documentation-only.
- For harness-only changes, run `bash scripts/harness_check.sh` when a POSIX shell is available. If unavailable, run an equivalent file-presence check and record the limitation.
- Failed or skipped verification must be recorded in `.harness/session-log.md` and, when useful, `docs/error-journal.md`.

## Safety Policy
- Use `scripts/safe_bash_guard.sh` as the boundary reference for dangerous shell patterns.
- Do not run destructive git, filesystem, database, migration, or force-push commands without explicit user instruction.
- Treat `config.json` as non-secret defaults only.

## Handoff Policy
Before ending a substantive session, update:
- `current-task.md`
- `.harness/session-state.json`
- `.harness/session-log.md`
- `docs/decisions.md` or `docs/error-journal.md` when a durable decision or failure was learned

The handoff must include completed work, changed files, verification results, open risks, and the recommended resume point.

## Recommended Skills
- `/start`: restore context and produce a Session Briefing.
- `/plan`: turn a request into a tracked plan.
- `/review`: inspect current diff for blockers and risks.
- `/commit`: perform pre-commit review and verification; do not commit unless the user asks.
- `/handoff`: seal session state for the next agent.

## Output Style
Be concise, concrete, and evidence-oriented. Lead with findings or outcomes, include commands that were run, and point to changed files when useful.
