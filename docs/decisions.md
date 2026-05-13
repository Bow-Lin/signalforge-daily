# Decisions

## Decision Log

### 2026-05-11 - Initialize Standard Project Harness
- Status: Accepted
- Context: The repository is a long-lived Python project with multiple CLIs, generated outputs, AI/network integrations, and agent-assisted development.
- Decision: Use a Standard Harness with protocol, state, verification, skills, and boundary scripts.
- Consequences: Future sessions should start with `/start`, record plans and verification evidence, and use `/handoff` before ending substantive work.

### 2026-05-11 - Keep External Skill Checkout Ignored
- Status: Accepted
- Context: `skills/ai-daily-digest/` is an external git checkout and should not be mixed into this repository history.
- Decision: Ignore only `skills/ai-daily-digest/` rather than the full `skills/` directory, so project harness skills can be tracked.
- Consequences: Harness skills under `skills/start`, `skills/plan`, `skills/review`, `skills/commit`, and `skills/handoff` remain eligible for version control.

### 2026-05-11 - Use Electron for v0.1 Desktop Wrapper
- Status: Superseded
- Context: The first v0.1 app shell used Electron because Rust/Cargo were not installed in the current Windows environment.
- Decision: Superseded by the Tauri decision below.
- Consequences: The React renderer was retained, but Electron main/preload files were removed.

### 2026-05-12 - Use Tauri for v0.1 Desktop Wrapper
- Status: Accepted
- Context: The desired architecture is Tauri App with React/Vue frontend, `src-tauri` Rust shell, and Python backend sidecar. Rust and Visual Studio C++ Build Tools were installed to make this locally verifiable.
- Decision: Implement the v0.1 desktop wrapper with Tauri + React + TypeScript under `app/`, Rust commands under `app/src-tauri/`, and a `digest-sidecar` launcher that delegates to the existing Python digest CLI.
- Consequences: The app follows the target desktop architecture and can be checked with Cargo. A later packaging step can replace the launcher sidecar with a frozen Python executable.

### 2026-05-12 - Rename Project to SignalForge Daily
- Status: Accepted
- Context: The product name should become SignalForge Daily, including the Python package namespace rather than only the desktop display name.
- Decision: Rename the Python package to `signalforge_daily`, the Python distribution to `signalforge-daily`, the npm app package to `signalforge-daily-app`, and the Tauri app metadata to SignalForge Daily.
- Consequences: CLI invocations now use `python -m signalforge_daily.<cli>`. Existing references to `news_collection` are intentionally removed except for the physical repository folder, which was left unchanged.

### 2026-05-13 - Treat Partial Feed Failures as Warnings
- Status: Accepted
- Context: A digest can be generated successfully even when some RSS feeds fail. Windows GBK output encoding also caused a completed run to exit non-zero while printing emoji status text.
- Decision: Keep digest CLI status output ASCII-safe, set Python subprocess encoding to UTF-8, and classify runs with written reports as successful when the only issue is partial feed failures or post-report status output.
- Consequences: Today shows successful reports with source warnings instead of a failed digest card, while real no-article, API, model, and write failures remain failed.

### 2026-05-13 - Make Today a Reading-First Surface
- Status: Accepted
- Context: The Today page exposed digest options, run status, report paths, and raw execution metadata before the actual article recommendations.
- Decision: Put the digest value summary and Top Picks first, localize visible Today copy to Chinese, and move low-frequency diagnostics into collapsed run details while preserving existing generation and report actions.
- Consequences: Today behaves more like a daily reading product. Tags, recommendation reasons, and favorites currently use compatible UI fallbacks until richer persisted article metadata is introduced.

## Template

### YYYY-MM-DD - Title
- Status: Proposed | Accepted | Superseded
- Context:
- Decision:
- Consequences:
