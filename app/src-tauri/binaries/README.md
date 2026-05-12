# Python Digest Sidecar

Packaged Tauri builds should place the compiled Python digest sidecar here using Tauri's target-triple naming convention, for example:

```text
digest-sidecar-x86_64-pc-windows-msvc.exe
digest-sidecar-x86_64-apple-darwin
digest-sidecar-aarch64-apple-darwin
digest-sidecar-x86_64-unknown-linux-gnu
```

For Windows development, build the launcher sidecar with:

```powershell
powershell -ExecutionPolicy Bypass -File .\src-tauri\sidecar\build-digest-sidecar.ps1
```

The launcher delegates to:

```bash
uv run python -m news_collection.digest_cli
```

from the repository root. A later packaging step can replace this launcher with a frozen Python backend executable created by PyInstaller, Nuitka, or a similar tool.
