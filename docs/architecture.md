# Architecture

## Overview
`signalforge_daily` is a Python 3.10+ project using a `src/` package layout. It provides command-line workflows for paper collection, blog tracking, and AI-assisted RSS digest generation.

## Main Components
- `src/signalforge_daily/cli.py`: paper/news collection CLI driven by `config.json` or command-line arguments.
- `src/signalforge_daily/graph.py`: LangGraph pipeline orchestration for collection and selection.
- `src/signalforge_daily/arxiv.py`: arXiv search integration.
- `src/signalforge_daily/storage.py`: paper result and metadata storage helpers.
- `src/signalforge_daily/pdf_tools.py`: PDF download and evidence extraction helpers.
- `src/signalforge_daily/blog_cli.py`: blog synchronization CLI.
- `src/signalforge_daily/blog_tracker/`: blog tracking domain logic, storage, and source adapters.
- `src/signalforge_daily/digest_cli.py`: AI daily digest CLI.
- `src/signalforge_daily/digest.py`: RSS/blog fetch, scoring, summarization, and Markdown report rendering.
- `src/signalforge_daily/digest_feeds.py`: default digest source list.
- `app/`: Tauri + React + TypeScript v0.1 desktop wrapper for configuring and running the daily digest locally.
- `app/src-tauri/`: Rust shell, Tauri commands, local persistence, report scanning, digest runner, and sidecar configuration.
- `app/src-tauri/sidecar/digest-sidecar/`: launcher sidecar that delegates to the Python digest CLI during v0.1 development.
- `app/src/`: React renderer pages for Today, Reports, Settings, and Setup.
- `scripts/graph_viz.py`: graph visualization utility.

## Data and Generated Outputs
Generated outputs are local project artifacts and should not be treated as source:
- `paper/`: paper metadata, PDF cache, and selected PDFs.
- `blog/`: blog sync outputs and source tracking.
- `output/`: digest Markdown reports.
- `logs/`: local runtime logs.
- selected desktop app workspaces: `app-config.json`, `runs/`, `reports/`, and `logs/` under the user-selected folder.

## External Services
- iFlow/OpenAI-compatible AI API via `IFLOW_API_KEY` or CLI argument.
- Optional Langfuse telemetry through environment variables.
- arXiv and RSS/blog HTTP sources.

## Harness Boundary
The harness lives in `AGENTS.md`, `current-task.md`, `docs/`, `.harness/`, `skills/`, and `scripts/`. Harness initialization must not change business code under `src/`.
