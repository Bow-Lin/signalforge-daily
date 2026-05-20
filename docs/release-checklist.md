# Release Checklist

Use this checklist before publishing a SignalForge Daily release.

## Version and Metadata

- [ ] `app/package.json` version updated.
- [ ] `app/src-tauri/Cargo.toml` version updated.
- [ ] `app/src-tauri/tauri.conf.json` version updated.
- [ ] App name is `SignalForge Daily`.
- [ ] Product name is `SignalForge Daily`.
- [ ] Identifier is `com.signalforge.daily`.
- [ ] Repository URL points to `https://github.com/Bow-Lin/signalforge-daily`.
- [ ] CHANGELOG updated.
- [ ] Release notes drafted.

## Build

- [ ] `cd app && npm install`
- [ ] `cd app && npm run build`
- [ ] `cd app && npm run sidecar:build`
- [ ] `cd app/src-tauri && cargo test`
- [ ] `cd app/src-tauri && cargo check`
- [ ] `uv run python -m pytest -q`
- [ ] `cd app && npm run package`
- [ ] Windows installer exists under `app/src-tauri/target/release/bundle/`.

## Installer QA

- [ ] Windows installer can install on a clean machine.
- [ ] Fresh install can open the app.
- [ ] App window title is `SignalForge Daily`.
- [ ] App icon appears in installer / app / tray.
- [ ] Installer can uninstall cleanly.
- [ ] Unsigned build limitation is documented if no code signing identity is used.

## Product Smoke

- [ ] First run enters Setup when no config exists.
- [ ] Demo Mode can be entered without API Key.
- [ ] Demo Mode shows Today sample digest.
- [ ] Demo Mode shows Reports preview.
- [ ] Demo Mode shows Sources sample quality data.
- [ ] Demo Mode can be cleared.
- [ ] API Key can be configured.
- [ ] Test Connection works with a valid provider.
- [ ] Generate Digest works with valid credentials.
- [ ] Reports preview works.
- [ ] Source enable / disable works.
- [ ] Relevance Profile saves.
- [ ] Automation settings save.
- [ ] Notification test works.
- [ ] Tray menu opens Today, Reports, and Sources.
- [ ] App restart restores config, runs, reports, source stats, and automation config.

## Privacy and Safety

- [ ] No API key committed.
- [ ] No signing certificate committed.
- [ ] No release token committed.
- [ ] `Copy diagnostic info` does not include API key, token, full config, or secret values.
- [ ] Logs do not intentionally print API keys.
- [ ] README privacy section links to `docs/privacy.md`.

## Documentation

- [ ] README updated.
- [ ] `docs/privacy.md` updated.
- [ ] `docs/troubleshooting.md` updated.
- [ ] `docs/smoke-test.md` updated.
- [ ] GitHub release notes prepared.
