# Current Task

## Goal
Implement SignalForge Daily v0.4 Packaging & Release readiness.

## Current Status
Completed. v0.4 release readiness is implemented with standardized metadata, About diagnostics, Demo Mode, release documentation, and verified build/test checks.

## Scope
- Standardize Tauri/app metadata for SignalForge Daily v0.4.0.
- Add package scripts for dev/build/Tauri/package workflows.
- Add Settings About / App Info with safe diagnostic copy and log folder access.
- Add Demo Mode with sample Today, Reports, and Sources data that is clearly marked and can be cleared.
- Add release documentation: README, privacy, troubleshooting, release checklist, changelog, and smoke test checklist.

## Out of Scope
- Research Mode.
- Paper Collection UX.
- Cloud sync, accounts, team workflows, or complex search.
- Full auto-updater implementation.
- Signing certificates, secrets, or release tokens.

## Validation Plan
- `cd app && npm run build`: passed.
- `cd app && npm run sidecar:build`: passed.
- `cd app/src-tauri && cargo test`: passed.
- `cd app/src-tauri && cargo check`: passed.
- `uv run python -m pytest -q`: passed.
- `cd app && npm run package`: release exe built, installer bundling failed on NSIS helper download timeout.
- `uv run python -m json.tool .harness/session-state.json`: passed.
- `git diff --check`: passed.
- PowerShell equivalent of `scripts/harness_check.sh`: passed.

## Known Risks
- Windows installers will be unsigned unless a signing identity is supplied outside the repository.
- Tauri runtime smoke testing for notifications/tray requires an interactive desktop session.
- `npm run package` built `app/src-tauri/target/release/signalforge-daily.exe`, but installer bundling failed because Tauri's NSIS helper download timed out.

## Next 3 Steps
1. Re-run `cd app && npm run package` on a network-stable release machine to produce NSIS/MSI installers.
2. Run `docs/smoke-test.md` against an installed build.
3. Prepare GitHub Release notes from `CHANGELOG.md`.

## Last Updated
2026-05-20T00:00:00+08:00
