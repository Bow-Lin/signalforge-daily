# Current Task

## Goal
Build a v0.1 local-first desktop app wrapper for the existing AI daily digest workflow: configure workspace/API key, generate today's digest, preview the report, and manage digest history.

## Current Status
Completed. The desktop app now follows the requested architecture: Tauri app, React/TypeScript frontend, `src-tauri` Rust shell, and a digest sidecar launcher that delegates to the existing Python backend CLI.

## Scope Completed
- Inspected the existing `news_collection.digest_cli` entrypoint and confirmed the runner contract:
  - `--hours`
  - `--top-n`
  - `--lang`
  - `--output`
  - `--iflow-key`
  - `--iflow-base-url`
  - `--iflow-model`
  - `--feed-concurrency`
  - `--ai-retries`
  - `--max-ai-articles`
- Added an `app/` Tauri + React + TypeScript desktop app subproject.
- Added `app/src-tauri/` Rust commands for local config, run history, report scanning, file actions, and digest generation.
- Added a Windows `digest-sidecar` launcher and build script under `app/src-tauri/sidecar/`.
- Configured Tauri `bundle.externalBin` for the sidecar path.
- Implemented Today, Reports, Settings, and first-run Setup pages.
- Implemented Markdown preview, report scanning, copy/open/reveal actions, and delete-from-list behavior for run records.
- Implemented error classification and recovery suggestions for missing API key, proxy errors, no articles, feed failures, model failures, write failures, and unknown failures.
- Implemented live `Test connection` behavior for OpenAI-compatible providers through a lightweight chat completions ping.
- Installed Rust and Visual Studio C++ Build Tools locally so the Tauri shell can be checked.
- Updated README, architecture docs, verification docs, decisions, and harness state.

## Out of Scope
- Paper collection UI, blog tracker UI, source management, scheduling, system tray, cloud sync, accounts, tags, full-text search, or core digest algorithm rewrites.
- Freezing the full Python backend into a standalone PyInstaller/Nuitka executable. v0.1 uses a sidecar launcher that calls the existing Python CLI through `uv`.

## Validation Commands
- `cd app && npm install`: passed.
- `cd app && npm run build`: passed.
- `cd app && npm run sidecar:build`: passed.
- `cd app/src-tauri && cargo check` from a Visual Studio Developer Command Prompt: passed.
- `uv run python -m pytest -q`: passed, 8 tests.
- `uv run python -m news_collection.digest_cli --help`: passed.

## Known Limitations
- A real end-to-end digest generation was not run because no API key was provided in this session.
- The v0.1 sidecar is a launcher around `uv run python -m news_collection.digest_cli`; later packaging can replace it with a frozen Python executable.
- `npm` prints a warning about unknown `electron-mirror` config in the current environment; it did not block install or build.

## Next 3 Steps
1. Run `cd app && npm run app:dev`, choose a workspace, configure a real API key, and generate one digest.
2. Add a live provider ping behind `Test connection` if the provider endpoint supports a cheap health check.
3. Add a packaging step that freezes the Python backend into a true standalone sidecar executable.

## Last Updated
2026-05-12T00:00:00+08:00
