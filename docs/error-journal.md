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

## Template

### YYYY-MM-DD - Title
- Area:
- Symptom:
- Impact:
- Root Cause:
- Workaround:
- Follow-up:
