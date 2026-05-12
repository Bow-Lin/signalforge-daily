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

## Template

### YYYY-MM-DD - Title
- Status: Proposed | Accepted | Superseded
- Context:
- Decision:
- Consequences:
