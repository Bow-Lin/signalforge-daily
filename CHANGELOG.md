# Changelog

## v0.4.0

### Added

- Packaging and release readiness for Windows x64.
- Standard app metadata for SignalForge Daily.
- `npm run tauri:dev` and `npm run package` command aliases.
- Settings About / App Info section with safe diagnostic copy.
- Open logs folder action.
- Demo Mode with sample Today digest, Reports preview, and Sources quality data.
- Privacy, troubleshooting, release checklist, and smoke test documentation.

### Changed

- App, Tauri, and npm package versions are aligned at `0.4.0`.
- Tauri identifier is standardized as `com.signalforge.daily`.
- README is rewritten as a Chinese-first product and release guide.
- Bundle targets are focused on Windows installer formats (`nsis`, `msi`).

### Fixed

- Automatic preflight failures, such as missing API key, now create failed RunRecords.
- Startup missed automation attempts consume the same-day scheduled slot to avoid duplicate automatic runs.

### Known Issues

- Windows installer builds are unsigned unless signing credentials are supplied outside the repository.
- Unsigned installers may trigger Windows SmartScreen.
- Auto-updater is not implemented in v0.4. Use GitHub Releases manually.
- Notification click behavior and tray actions should be smoke tested in an interactive Tauri runtime session before release.
