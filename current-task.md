# Current Task

## Goal
Fix v0.3 Automation scheduler blockers found during the commit-main review gate.

## Current Status
Completed and ready to land through the guarded commit-main workflow. Automatic preflight failures now create failed `RunRecord`s, and startup-missed runs consume the same-day scheduled slot.

## Scope Completed
- Added Rust regression tests for failed preflight run records and startup-missed scheduled-slot consumption.
- Refactored initial digest run record construction into a shared helper.
- Changed missing API key preflight failures to persist a failed run, emit a failed digest event, and send automation failure notifications when applicable.
- Changed startup-missed scheduler handling so successful, failed, and skipped startup catch-up attempts also mark the scheduled slot consumed for that date.
- Added an active-run skip path for startup-missed automation so it records a skip reason instead of trying to start a concurrent digest.

## Out of Scope
- Live scheduled digest execution with real API credentials.
- Notification click runtime smoke testing.
- Broader scheduler redesign or OS login-start integration.
- Live Tauri runtime smoke testing unless explicitly requested.

## Validation Commands
- `cd app/src-tauri && cargo test`: passed.
- `cd app/src-tauri && cargo check`: passed.
- `cd app && npm run build`: passed.
- `uv run python -m pytest -q`: passed.
- `cd app && npm run sidecar:build`: passed.

## Known Risks
- Live notification/tray behavior still needs runtime smoke testing in the Tauri shell.
- Live scheduled generation was not run because it needs user-local provider credentials and schedule timing.

## Next 3 Steps
1. Perform live Tauri smoke testing for automation, notifications, and tray actions.
2. In the Tauri app, enable automation with a near-future time and verify one scheduled run is created.
3. Temporarily remove the API key and verify Today shows the failed automatic run with the missing API key recovery card.

## Last Updated
2026-05-20T00:00:00+08:00
