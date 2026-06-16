# Current Task

## Goal
Reduce repeated clicks in the desktop app by streamlining common actions, adding action feedback, remembering page state, and supporting keyboard shortcuts.

## Current Status
Completed. Common Today, Reports, Sources, Settings, and feedback actions now require fewer repeated clicks and give visible feedback.

## Scope
- Keep high-frequency Today actions visible: view latest report, copy selected picks, and regenerate.
- After manual generation succeeds, keep/focus Today on the latest result and show a toast action to view the full report; after failure, focus the recovery card.
- Add unified toast feedback with undo where local state can be safely reversed.
- Remember last route, selected report, and key collapsed/expanded UI state.
- Add keyboard shortcuts for regenerate, open latest report, settings, and Sources search focus.

## Out of Scope
- Python digest algorithm changes.
- Tauri persistence schema changes unless required for undo safety.
- Browser visual QA if no runnable Tauri renderer is available.

## Validation Plan
- Focused TypeScript UI helper test: failed before implementation because `uiState` helper was missing; passed after implementation.
- `cd app && npm run build`: passed.
- `cd app/src-tauri && cargo check`: passed.
- `cd app/src-tauri && cargo test`: passed, 5 tests.
- `uv run python -m json.tool .harness/session-state.json`: passed.
- PowerShell equivalent of `scripts/harness_check.sh`: passed.
- Browser smoke via Vite: reached Setup and Demo Mode, verified top Today actions and `/` Sources search focus; full Tauri bridge flows require Tauri shell because plain Vite lacks `window.__TAURI__`.

## Known Risks
- Runtime-only interactions such as scrolling/focus are best verified in the Tauri shell; build can only verify integration statically.
- Undo for destructive physical file deletion remains out of scope; direct delete already warns that it cannot be undone.
- "从列表移除" is now non-destructive and keeps run metadata so undo can restore the full report card.

## Next 3 Steps
1. Run `cd app && npm run tauri:dev` and smoke test real Tauri actions: manual generation completion toast, Reports undo, feedback undo, Settings undo.
2. Consider adding renderer component tests if a React test runner is introduced.
3. If users need cleanup of old run JSON after non-destructive report removal, define a separate compaction policy instead of coupling it to UI removal.

## Last Updated
2026-06-16T00:00:00+08:00
