# Verification

## Project Type
Python 3.10+ package using `pyproject.toml`, `uv`, and `pytest`.

## Environment Setup
Preferred:

```bash
uv sync
```

Alternative:

```bash
pip install -r requirements.txt
pip install -e .
```

## Standard Verification Matrix
| Change Type | Commands |
| --- | --- |
| Python business logic | `uv run python -m pytest -q` |
| Digest parser/report behavior | `uv run python -m pytest -q tests/test_digest.py` plus full pytest when shared code changes |
| CLI behavior | `uv run python -m pytest -q`; optionally run the relevant `uv run python -m signalforge_daily.<cli> --help` |
| Desktop app renderer | `cd app && npm install` when dependencies are missing, then `npm run build` |
| Tauri shell | `cd app && npm run sidecar:build`, then `cd app/src-tauri && cargo check` from a Visual Studio Developer Command Prompt on Windows |
| Desktop packaging | `cd app && npm run package`; installers should appear under `app/src-tauri/target/release/bundle/`. Record bundler download/signing limitations if packaging cannot complete. |
| Harness or docs only | `bash scripts/harness_check.sh` when available; otherwise equivalent file-presence check |
| Graph visualization utility | `uv run python scripts/graph_viz.py --format mermaid --out /tmp/graph.mmd` on POSIX, or a local temp path on Windows |

## Runtime Smoke Commands
Use these when the task affects a specific CLI and required credentials/network are available:

```bash
uv run python -m signalforge_daily.cli --config config.json
uv run python -m signalforge_daily.blog_cli --source all
uv run python -m signalforge_daily.digest_cli --hours 24 --top-n 15 --lang zh
cd app && npm run app:dev
```

## Harness Check
Primary command:

```bash
bash scripts/harness_check.sh
```

If `bash` is unavailable, run an equivalent file existence check for all files listed in `scripts/harness_check.sh` and record that the shell script itself was not executed.

## Failure and Skipped Verification Policy
When verification fails or cannot run:
1. Record the command, result, and reason in `.harness/session-log.md`.
2. Add recurring or non-obvious failures to `docs/error-journal.md`.
3. State the residual risk in the final response or handoff.
4. Do not claim completion without either passing evidence or an explicit skipped-verification rationale.
