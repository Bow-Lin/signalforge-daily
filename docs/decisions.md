# Decisions

## Decision Log

### 2026-07-06 - Use Radar-Style App Icon
- Status: Accepted
- Context: SignalForge Daily needs a Windows taskbar icon that remains recognizable at small sizes and reflects signal monitoring plus daily intelligence.
- Decision: Use the Signal Radar direction: a dark rounded-square tile with cyan radar arcs, a central signal node, and a small amber pulse. Keep the Tauri bundle icon path as `app/src-tauri/icons/icon.ico` and maintain a same-source PNG preview beside it.
- Consequences: The taskbar icon now emphasizes the SignalForge brand rather than a generic document/digest metaphor. Future icon refinements should preserve high contrast and simple geometry for 16px and 24px Windows shell sizes.

### 2026-06-24 - Route Digest Reports into Obsidian Vaults
- Status: Accepted
- Context: Users want generated digest Markdown to appear in Obsidian for reading, editing, tagging, and linking, while SignalForge Daily still needs local workspace state for config, runs, logs, and metadata.
- Decision: Treat Obsidian integration as a report-output routing feature: keep `workspacePath` outside the vault, and set `outputPath` to a `SignalForge Daily` subfolder inside the chosen Obsidian Vault.
- Consequences: Generated Markdown can be indexed and edited by Obsidian without syncing app metadata or logs. Reports still scan only the configured output directory, so the app should write digest files directly under the Obsidian report folder unless recursive scanning is added later.

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

### 2026-05-14 - Gate Today on First-Run Readiness
- Status: Accepted
- Context: The desktop app should not drop first-time users into Today when required local workspace or AI provider fields are missing.
- Decision: Treat `workspacePath`, `outputPath`, API key, and model as the minimum readiness boundary. In setup mode, saving and entering Today requires those fields plus a successful connection test; Today generation actions remain disabled until the same boundary is satisfied.
- Consequences: First-run users are guided through configuration before generation. Existing Settings still allows saving partial edits, but an incomplete config routes back through Setup on restart.

### 2026-05-18 - Deduplicate Digest Articles by Normalized Title
- Status: Accepted
- Context: Different RSS sources can publish or syndicate the same article under different URLs, which link-only deduplication does not catch.
- Decision: Use normalized article title as the primary deduplication key and fall back to link when the title is empty. When duplicates exist, keep the most recently published item.
- Consequences: Duplicate syndicated content is removed before filtering, AI scoring, and reporting. Distinct articles with exactly the same normalized title can be merged, which is an intentional v0.1 tradeoff.

### 2026-05-18 - Add Source Quality and Trust as Local v0.2 Data
- Status: Accepted
- Context: v0.2 needs source control and relevance tuning without adding schedulers, cloud sync, team workflows, complex search, or paper mode.
- Decision: Persist SourceConfig, RelevanceProfile, SourceRunStat, and ItemFeedback in the local desktop workspace. Pass enabled sources and relevance profile into the existing Python digest CLI as JSON files, then read per-source run stats back from a JSON output file.
- Consequences: The v0.1 one-click runner remains intact while source enablement, source health, noisy/failed hints, relevance prompt context, Quality Summary, and local feedback become visible and durable.

### 2026-05-18 - Polish v0.2.5 as a Desktop Reading Tool
- Status: Accepted
- Context: v0.2 had the necessary functionality, but the UI read too much like a management dashboard: heavy sidebar, oversized source cards, mixed button hierarchy, and English feedback/status labels.
- Decision: Keep behavior unchanged and introduce shared UI primitives plus tokenized styling. Today is treated as the reading-first surface, Sources as a compact quality-management surface, Reports as a two-column reading surface, and Settings as grouped local configuration.
- Consequences: The app should feel lighter and more local-first without adding automation, tray, notification, paper/research, cloud, or account features. Future UI work should reuse the shared page header, status badge, empty/loading/error states, and button/card tokens instead of page-specific variants.

### 2026-05-18 - Add Automation as Local Desktop Runtime
- Status: Accepted
- Context: v0.3 needs daily habits without cloud accounts or a separate task system. Existing digest generation already creates durable local run records and emits progress events.
- Decision: Store `AutomationConfig` in the local `app-config.json`, run a lightweight Tauri-side scheduler thread, and reuse the existing digest runner with a `trigger` field for manual, scheduled, and startup-missed runs. Use the Tauri notification plugin from the renderer for permission-aware notifications and Tauri tray APIs for desktop menu actions.
- Consequences: Automatic runs work while the desktop app is running and never run concurrently with a manual digest. Missed-startup and scheduled skips are recorded in local automation metadata. OS-level startup registration is still a later feature, so the app must be launched for the scheduler to operate.

### 2026-05-20 - Treat Automation Preflight Failures as Runs
- Status: Accepted
- Context: Scheduled and startup-missed digest attempts can fail before the Python sidecar starts, for example when the API key is missing. Users still need those failures to be visible, recoverable, and durable in Today.
- Decision: Build and persist failed `RunRecord`s for digest runner preflight failures once a workspace is configured. A startup-missed attempt or skip also consumes the same day's scheduled slot so automatic runs do not repeat unexpectedly.
- Consequences: Automation failures remain visible through the same local history and error recovery UI as sidecar failures. The scheduler stays single-run-per-day by default, while manual retry remains available to the user.

### 2026-05-20 - Keep v0.4 Release Readiness Local and Unsigned
- Status: Accepted
- Context: v0.4 should make SignalForge Daily installable and demoable without adding cloud services, auto-updates, accounts, or signing secrets to the repository.
- Decision: Standardize app metadata at `v0.4.0`, target Windows installer formats, add local Demo Mode and safe diagnostic copy, and document unsigned installer limitations. Auto-update is represented only as a GitHub Releases link.
- Consequences: Users can try the app without API credentials and release maintainers have a checklist, but official distribution still needs a signing identity and a stable release machine or CI cache for Tauri bundler dependencies.

### 2026-05-27 - Persist Report History Removals as Tombstones
- Status: Accepted
- Context: Reports history is assembled from successful run records and Markdown files scanned from the configured reports folder. Deleting only the run record made the same Markdown file reappear as an unlinked report with missing selected-count metadata.
- Decision: Store removed report paths in `metadata/hidden-reports.json` and have report scanning skip those paths. Direct deletion is a separate confirmed action that deletes the Markdown file and matching run record.
- Consequences: "Remove from list" is non-destructive and durable across app restarts, while "delete report" performs local file deletion only after UI confirmation. Direct deletion currently removes the Markdown file and matching run record, not generated side outputs.

### 2026-05-27 - Treat Quiet Feeds as Successful
- Status: Accepted
- Context: RSS fetches can succeed while returning no articles in the requested time window, especially for low-frequency sources such as official developer blogs. The previous accounting reported those as `empty feed` failures.
- Decision: Count a feed as successful when its request and parsing complete without exception, even if it contributes zero in-window articles. Keep HTTP, TLS, timeout, and parser exceptions as failed sources.
- Consequences: Source warnings now focus on actionable fetch failures. Undated feeds still produce no articles because assigning synthetic dates would repeatedly surface stale content.

### 2026-06-16 - Keep Frequent Desktop Actions Local and Immediate
- Status: Accepted
- Context: Today, Reports, Sources, and Settings had useful actions, but several high-frequency flows required repeated expansion, lacked feedback, or lost page context across reloads.
- Decision: Keep common Today actions visible in the header, store lightweight UI state in renderer `localStorage`, and use a shared renderer toast for successful actions and safe undo. Keep destructive report file deletion as confirmation-only with no undo, while non-destructive history removal can undo by restoring the hidden-report tombstone.
- Consequences: Users can jump to the latest report, copy picks, regenerate, reopen prior page state, and recover from accidental local changes faster. Full runtime validation still belongs in the Tauri shell because the plain Vite renderer lacks Tauri `invoke` and event APIs.

## Template

### YYYY-MM-DD - Title
- Status: Proposed | Accepted | Superseded
- Context:
- Decision:
- Consequences:
