# Current Task

## Goal
Fix Reports history removal so removed reports stay hidden, and add confirmed report deletion.

## Current Status
Completed. Report history removals now persist a hidden-report tombstone, and direct report deletion requires confirmation before deleting the Markdown file.

## Scope
- Persist report-history removals so Markdown files are not re-listed after the associated run is removed.
- Add a direct delete action for reports.
- Require a confirmation dialog before direct deletion.
- Keep report deletion scoped to the selected Markdown report and its local run record.

## Out of Scope
- Bulk delete or undo.
- Changing digest generation behavior.
- Deleting generated HTML/JSON side outputs.
- Runtime installer or packaging changes.

## Validation Plan
- `cd app/src-tauri && cargo test report`: failed before implementation because removal/deletion helpers were missing; passed after implementation.
- `cd app/src-tauri && cargo test`: passed, 4 tests.
- `cd app/src-tauri && cargo check`: passed.
- `cd app && npm run build`: passed.
- `uv run python -m json.tool .harness/session-state.json`: passed.
- PowerShell equivalent of `scripts/harness_check.sh`: passed, 18 files present.

## Known Risks
- Runtime Tauri UI smoke was not run in this session; behavior is covered by Rust tests and TypeScript build.
- Direct deletion intentionally deletes only the Markdown report file and matching run record, not possible HTML/JSON side outputs.

## Next 3 Steps
1. Optionally run `cd app && npm run tauri:dev` and smoke test Reports remove/delete in the desktop shell.
2. If side outputs should also be deleted, define the expected file cleanup policy before implementation.
3. Continue with normal app release QA.

## Last Updated
2026-05-27T00:00:00+08:00
