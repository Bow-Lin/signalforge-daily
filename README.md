# SignalForge Daily

SignalForge Daily is a local-first technical digest tool for AI, agents, coding, EDA, and adjacent engineering signals. It combines a Tauri desktop app with the existing Python collection and digest CLIs.

The desktop app is the primary product surface: configure a local workspace and an OpenAI-compatible API key, generate a daily digest, read Chinese-first Top Picks, inspect source warnings, and open historical Markdown reports.

## What It Does

- Generates AI-assisted technical digests from built-in RSS and blog sources.
- Presents Today as a Chinese-first reading page with summary stats, Top Picks, recommendation reasons, and collapsed run details.
- Treats partial feed failures as warnings when a usable report was generated.
- Stores app data locally in the workspace you choose.
- Keeps Python CLIs available for digest generation, paper collection, blog tracking, and graph visualization.

## Project Layout

```text
app/                         Tauri + React + TypeScript desktop app
app/src/                     React renderer pages and components
app/src-tauri/               Rust shell, commands, persistence, sidecar runner
app/src-tauri/sidecar/       digest-sidecar launcher for the Python CLI
src/signalforge_daily/       Python package and business logic
tests/                       pytest coverage for digest behavior
docs/                        architecture, verification, decisions, error journal
.harness/                    durable session state and log
```

Generated outputs stay local and are not source files: `paper/`, `blog/`, `output/`, `logs/`, app workspace `runs/`, app workspace `reports/`, and app workspace `logs/`.

## Requirements

- Python `>=3.10`
- `uv` for Python environment management
- Node.js and npm for the desktop renderer
- Rust and the Windows C++ build tools for Tauri shell checks/builds
- An iFlow/OpenAI-compatible API key for live digest generation

## Desktop App

Install dependencies and run the local app:

```bash
cd app
npm install
npm run app:dev
```

In the app:

1. Choose a local workspace folder.
2. Configure the API key, model, base URL, and proxy settings.
3. Pick digest defaults such as language and time range.
4. Click `生成今日摘要` on Today.

The selected workspace contains:

```text
app-config.json
runs/
logs/
reports/
```

The v0.1 sidecar launcher delegates to:

```bash
uv run python -m signalforge_daily.digest_cli
```

Useful app commands:

```bash
cd app
npm run build
npm run sidecar:build
npm run tauri:build
```

## Python Setup

Recommended:

```bash
uv sync
```

Set the API key for CLI usage:

```bash
export IFLOW_API_KEY=your_key
```

On Windows PowerShell:

```powershell
$env:IFLOW_API_KEY = "your_key"
```

Optional Langfuse telemetry:

```bash
export LANGFUSE_PUBLIC_KEY=your_public_key
export LANGFUSE_SECRET_KEY=your_secret_key
export LANGFUSE_HOST=https://cloud.langfuse.com
```

## Digest CLI

Generate a Chinese digest:

```bash
uv run python -m signalforge_daily.digest_cli --hours 24 --top-n 15 --lang zh
```

Write to a specific Markdown path:

```bash
uv run python -m signalforge_daily.digest_cli \
  --hours 24 \
  --top-n 15 \
  --lang zh \
  --output ./output/digest-$(date +%Y%m%d).md \
  --feed-concurrency 10 \
  --ai-batch-size 10 \
  --ai-retries 1 \
  --max-ai-articles 120
```

Use a custom feed list:

```bash
uv run python -m signalforge_daily.digest_cli --feeds-file ./my_feeds.txt
```

`my_feeds.txt` accepts `name<TAB>rss_url` or a bare RSS URL per line:

```text
simonwillison.net	https://simonwillison.net/atom/everything/
https://example.com/rss.xml
```

## Other CLIs

Run paper collection:

```bash
uv run python -m signalforge_daily.cli \
  --topic "RTL 代码生成 且使用cvdp数据集或RealBench数据集" \
  --requirements "使用cvdp数据集或RealBench数据集" \
  --content-type paper \
  --start "2025-09-01" \
  --end "2026-01-15" \
  --tz "Asia/Shanghai" \
  --iflow-model "qwen3-max" \
  --max-results 5 \
  --pdf-max-chars 16000
```

Run from `config.json`:

```bash
uv run python -m signalforge_daily.cli --config config.json
```

Run blog tracking:

```bash
uv run python -m signalforge_daily.blog_cli --source all
```

Print the LangGraph pipeline as Mermaid:

```bash
uv run python scripts/graph_viz.py --format mermaid
```

## Verification

For normal Python changes:

```bash
uv run python -m pytest -q
```

For desktop renderer changes:

```bash
cd app
npm run build
```

For Tauri shell or sidecar changes:

```bash
cd app
npm run sidecar:build
cd src-tauri
cargo check
```

For docs or harness-only changes, run:

```bash
bash scripts/harness_check.sh
```

If Bash is unavailable on Windows, run an equivalent file-presence check and record the limitation in `.harness/session-log.md`.

## Troubleshooting

### `ModuleNotFoundError: No module named 'signalforge_daily'`

Run from the repository root and prefer `uv run`:

```bash
uv run python -m signalforge_daily.digest_cli --help
```

### `uv` cannot fetch build dependencies

If `uv run python -m pytest -q` cannot fetch `setuptools` or other build dependencies because of a transient TLS/network issue, use the local virtual environment when available:

```powershell
$env:PYTHONPATH = "src"
.venv/Scripts/python.exe -m pytest -q
```

### Proxy errors such as `127.0.0.1:7890`

Unset proxy variables if the local proxy daemon is not running:

```bash
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
```

On PowerShell:

```powershell
Remove-Item Env:http_proxy, Env:https_proxy, Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:ALL_PROXY, Env:all_proxy -ErrorAction SilentlyContinue
```

### API keys and generated files

Do not commit secrets. `.env` is local only, and API keys should come from environment variables or the desktop app settings. Generated report/output directories are local artifacts, not source.
