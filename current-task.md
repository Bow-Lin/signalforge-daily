# Current Task

## Goal
Let users route generated digest Markdown into an Obsidian Vault while keeping SignalForge Daily workspace metadata outside the vault.

## Current Status
Completed. Settings now has an Obsidian output shortcut that maps a chosen vault folder to a `SignalForge Daily` report subfolder.

## Scope
- Add a tested path helper for Obsidian report output.
- Add a Settings action for choosing an Obsidian Vault as the digest report destination.
- Preserve existing workspace, run records, logs, and metadata behavior.

## Out of Scope
- Obsidian plugin development.
- Recursive report scanning.
- Markdown template/frontmatter changes.
- Moving existing reports automatically.

## Validation Plan
- Focused TypeScript helper test: passed.
- `cd app && npm run build`: passed.
- `uv run python -m json.tool .harness/session-state.json`: passed.
- PowerShell equivalent of `scripts/harness_check.sh`: passed.
- `bash scripts/harness_check.sh`: skipped because Bash is unavailable in this Windows session.

## Known Risks
- Runtime Tauri folder-picker smoke testing was not run yet.
- Reports still scan only the configured output directory, so generated reports should remain directly under the Obsidian `SignalForge Daily` folder.

## Next 3 Steps
1. In the app Settings page, choose the normal workspace folder separately from the Obsidian Vault.
2. Use the new Obsidian button beside the report output field and save settings.
3. Generate a digest and confirm the Markdown appears in `<vault>/SignalForge Daily/`.

## Last Updated
2026-06-24T11:24:00+08:00
