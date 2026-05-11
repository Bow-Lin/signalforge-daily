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

## Template

### YYYY-MM-DD - Title
- Area:
- Symptom:
- Impact:
- Root Cause:
- Workaround:
- Follow-up:
