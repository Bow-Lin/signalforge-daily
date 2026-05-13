# Current Task

## Goal
Upgrade the Today page from a run-status panel into a Chinese-first daily technical digest reading page.

## Current Status
Completed. Today now opens as a Chinese-first reading page: summary value and Top Picks appear before technical run details, and low-frequency diagnostics are collapsed.

## Scope Completed
- Chinese-localize visible Today-page copy and navigation labels.
- Add a Today summary overview with friendly status, generation time, source count, selected article count, and Top Picks count.
- Promote Top Picks into article cards with source, tags, recommendation reason, and reader actions.
- Move report path, duration, current step, failed feeds, raw fetched count, and logs into a collapsed run details section.
- Replace raw `Unknown` output with user-friendly fallback text such as `未记录`.
- Keep existing generation, report opening, folder reveal, and copy behavior intact.

## Out of Scope
- Full feed management UI.
- Changing the digest ranking/summarization algorithm.
- Freezing the Python backend into a standalone executable.
- Persistent favorites, read-later state, or interest feedback storage.
- Auto-generation scheduling and system notifications.

## Validation Commands
- `cd app && npm run build`: passed.
- Browser/IAB visual smoke check: skipped because no callable Browser/IAB tool was exposed in this session, and the Vite renderer depends on the Tauri `invoke` runtime for real app data.

## Known Limitations
- A live digest rerun depends on API credentials and network conditions.
- Standard `uv run python -m pytest -q` may still be blocked by PyPI TLS fetching `setuptools`; use local `.venv` with `PYTHONPATH=src` if needed.
- Recommendation reasons and tags may use UI fallbacks when historical report data does not include structured fields.

## Next 3 Steps
1. Run `npm run app:dev` and visually inspect the Tauri-rendered Today page with the real local workspace data.
2. Decide whether Favorites/Sources should become real routes or stay as disabled retention placeholders for now.
3. Commit the accumulated SignalForge Daily rename, RSS-warning handling, and Today reading-page redesign after review.

## Last Updated
2026-05-13T09:00:17+08:00
