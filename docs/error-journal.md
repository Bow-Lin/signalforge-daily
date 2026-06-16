# Error Journal

## Known Failures and Workarounds

### 2026-05-11 - POSIX shell unavailable in current Windows session
- Area: Harness verification
- Symptom: `bash` and `sh` were not found in the current PowerShell environment.
- Impact: `bash scripts/harness_check.sh` and `bash -n scripts/run_digest_with_retry.sh` cannot be executed in this session.
- Workaround: Run an equivalent PowerShell file-presence check for harness initialization, and verify shell scripts later in Git Bash, WSL, Linux, or CI.
- Follow-up: Consider adding a PowerShell harness check if Windows-only operation becomes common.

### 2026-05-11 - RSS fetch proxy errors to 127.0.0.1:7890
- Area: Digest runtime
- Symptom: RSS fetch logs may show proxy errors when local proxy environment variables point to an inactive proxy.
- Impact: Feed fetch can fail even when internet is available.
- Workaround: Unset `http_proxy`, `https_proxy`, `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, and `all_proxy`, or start the local proxy.

### 2026-05-12 - uv editable rebuild cannot fetch setuptools
- Area: Python verification
- Symptom: After renaming the package to `signalforge-daily`, `uv run python -m pytest -q` attempted to rebuild the editable project and failed to fetch `setuptools>=68.0` from PyPI with TLS handshake EOF.
- Impact: Standard uv verification cannot complete until the build backend is available locally or network access to PyPI works.
- Workaround: Use the existing local virtual environment with `PYTHONPATH=src`, for example `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -q` on Windows.
- Follow-up: Rerun standard `uv run python -m pytest -q` in a network-stable environment or preinstall/cache `setuptools` in the uv environment.

### 2026-05-13 - Windows GBK encoding failed completed digest runs
- Area: Desktop digest runner
- Symptom: A run with a written Markdown report and successful AI calls was stored as `failed` because Python raised `UnicodeEncodeError` while printing `[digest] ✅ Done!` to a GBK-encoded Windows subprocess stream.
- Impact: Today showed `Digest failed` and `feed_fetch_failed` even though the report was usable.
- Root Cause: CLI status output used emoji/non-ASCII text after report generation, and the Tauri runner classified any non-zero exit as a failed digest.
- Workaround: Use ASCII-safe CLI status output, set `PYTHONIOENCODING=utf-8`/`PYTHONUTF8=1` for runner subprocesses, and migrate existing report-backed partial feed failures to success with warnings.
- Follow-up: Prefer machine-readable runner events in a later version instead of parsing human log text.

### 2026-05-20 - Tauri NSIS helper download timed out during packaging
- Area: Desktop packaging
- Symptom: `npm run package` built `app/src-tauri/target/release/signalforge-daily.exe`, then failed while bundling the NSIS installer with `failed to bundle project timeout: global` during download of `nsis_tauri_utils.dll`.
- Impact: The release executable was produced, but `bundle/nsis/*.exe` and `bundle/msi/*.msi` installers were not produced in this environment.
- Root Cause: Packaging depends on downloading Tauri bundler helper binaries when they are not already cached; the current network request timed out.
- Workaround: Re-run `cd app && npm run package` on a network-stable machine or pre-cache Tauri NSIS/WiX bundler dependencies. Installer signing still requires external credentials and is not stored in the repo.
- Follow-up: Add CI or a release machine with cached bundler dependencies for repeatable installer builds.

### 2026-05-27 - Default RSS source failures
- Area: Digest RSS source health
- Symptom: Several default sources were reported as failures: OpenAI Developers Blog, blog.pixelmelt.dev, chadnauseam.com, paulgraham.com, rachelbythebay.com, and tedunangst.com.
- Impact: Successful digest runs could show noisy source warnings, including `empty feed` for sources that fetched successfully but had no dated articles in the requested time window.
- Root Cause: `fetch_all_feeds` treated any successful fetch returning zero in-window articles as `empty feed`. Separately, `blog.pixelmelt.dev` returned Cloudflare HTTP 530, while `rachelbythebay.com` and `tedunangst.com` timed out or failed TLS from this environment. Chad Nauseam and the Paul Graham aaronsw feed are reachable but omit item dates, so they produce no dated articles.
- Workaround: Successful empty fetches now count as successful sources, and the currently unreachable `blog.pixelmelt.dev`, `rachelbythebay.com`, and `tedunangst.com` feeds were removed from the default list.
- Follow-up: Existing user workspaces with persisted source configs may still need these sources disabled manually from the Sources page.

### 2026-06-16 - Plain Vite renderer lacks Tauri bridge
- Area: Desktop renderer QA
- Symptom: Opening `http://127.0.0.1:5173` in a normal browser renders Setup/Demo UI, but console logs show Tauri `invoke`/`listen` failures such as missing `transformCallback` or `invoke`.
- Impact: Browser smoke can verify static renderer layout, Demo Mode, and local UI state interactions, but cannot fully validate real workspace, report, notification, or digest runner commands.
- Root Cause: The React renderer expects Tauri runtime globals when not in Demo Mode; Vite alone does not provide `window.__TAURI__` command and event bridges.
- Workaround: Use `cd app && npm run tauri:dev` for full runtime QA. Use plain Vite only for limited renderer smoke tests, preferably Demo Mode interactions.
- Follow-up: Consider adding a browser-only mock bridge if routine renderer QA outside Tauri becomes important.

## Template

### YYYY-MM-DD - Title
- Area:
- Symptom:
- Impact:
- Root Cause:
- Workaround:
- Follow-up:
